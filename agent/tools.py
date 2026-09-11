"""Homework 1: the remaining commerce-agent tools.

The three lecture tools (`search_help_center`, `get_order`, `issue_refund`)
are implemented in agent/agent.py and are worked examples of the pattern:
check permissions first, go through agent/db.py for data, and return a
structured dict, never a prose error. The homework tools follow the same
pattern. agent/agent.py already wraps each function below as an SDK tool, so
once a function works here it works in chat with no further wiring.

Result convention (see agent/auth.py):
  - Success: a dict with "ok": True plus the payload fields named in each
    docstring.
  - Failure: {"ok": False, "error": <code>, "reason": <human-readable str>}.

Run the contract tests with: uv run pytest tests/test_hw_holes.py -k hw1
They are marked xfail and flip to passing as you implement each function.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from agent import db
from agent.auth import AuthContext, can_cancel_order, permission_denied
from agent.config import load_facts
from agent.helpcenter import load_policy_docs
from agent.killswitch import kill_switch

MAX_SEARCH_LIMIT = 25
DEFAULT_ORDER_LIMIT = 20
FIND_ORDER_MAX_RESULTS = 5
# Deliberately loose: a shopper describes a product from memory, so we would
# rather return a weak match with its score than miss the order entirely.
FIND_ORDER_MIN_SCORE = 60.0


# Words that describe the purchase rather than the product. They must not
# vote on a match: "the vase I bought last week" scored 100 against every
# order before this filter, because the token "i" is a substring of
# "Midnight", "Organizer", and most other titles.
_QUERY_STOPWORDS = frozenset(
    """a an the my mine me i it its this that these those one some any
    of for from with about on in at to by and or but is was were be been
    order orders ordered purchase purchased bought buy buying item items
    thing things product find show get where when please need want
    last week weeks month months year years day days ago recent recently
    yesterday today back second""".split()
)
# A short token may still support a fuzzy score, but only a substantial one
# may claim a perfect substring match.
_MIN_TOKEN_LEN = 3
_MIN_SUBSTRING_TOKEN_LEN = 4


def _content_tokens(query: str) -> list[str]:
    """The product-describing words of a natural-language query."""
    return [
        token
        for token in query.lower().split()
        if len(token) >= _MIN_TOKEN_LEN and token not in _QUERY_STOPWORDS
    ]


def _title_match_score(query: str, title: str) -> float:
    """Fuzzy similarity (0-100) between a natural-language query and a title.

    Scored per content token so the filler in "earmuffs I bought last week"
    neither drags down nor inflates the match against "Wool Earmuffs".
    """
    t = title.lower().strip()
    if not t:
        return 0.0

    tokens = _content_tokens(query)
    if not tokens:
        # Nothing but filler; fall back to whole-string similarity.
        q = query.lower().strip()
        return SequenceMatcher(None, q, t).ratio() * 100 if q else 0.0

    best = SequenceMatcher(None, " ".join(tokens), t).ratio() * 100
    title_tokens = t.split()
    for token in tokens:
        for title_token in title_tokens:
            if len(token) >= _MIN_SUBSTRING_TOKEN_LEN and (
                token in title_token or title_token in token
            ):
                best = max(best, 100.0)
            else:
                best = max(best, SequenceMatcher(None, token, title_token).ratio() * 100)
    return best


def get_policy(ctx: AuthContext, policy_id: str) -> dict[str, Any]:
    """Fetch one policy doc by its exact id. Risk tier: read.

    Every role may read every policy doc (the corpus is public help-center
    content), so this tool needs no permission check.

    Args:
        ctx: The caller's auth context. Unused here, but every tool takes it.
        policy_id: An exact policy id, e.g. "cw-returns" or
            "store-juniper-home-goods-policy". Matching is exact and
            case-sensitive; ids are the `policy_id` front-matter field of the
            files in data/policies/.

    Returns:
        On success: {"ok": True, "policy_id": str, "title": str,
        "audience": str, "body": str} where body is the markdown body of the
        doc without the front matter.
        If no doc has that id: {"ok": False, "error": "not_found",
        "reason": ...} naming the id that was requested.

    Implementation notes:
        agent.helpcenter.load_policy_docs() returns every parsed doc.
    """
    for doc in load_policy_docs():
        if doc.policy_id == policy_id:
            return {
                "ok": True,
                "policy_id": doc.policy_id,
                "title": doc.title,
                "audience": doc.audience,
                "body": doc.body,
            }
    return {
        "ok": False,
        "error": "not_found",
        "reason": f"no policy doc with id {policy_id!r}",
    }


def search_products(
    ctx: AuthContext,
    query: str,
    store: str | None = None,
    max_price_usd: float | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Search the product catalog. Risk tier: read.

    Every role may search products. Matching is deterministic keyword
    matching, not semantic search: a product matches when every whitespace
    token of `query` appears case-insensitively as a substring of the
    product's title or description.

    Args:
        ctx: The caller's auth context.
        query: Free-text query. Must be non-empty after stripping whitespace;
            otherwise return {"ok": False, "error": "invalid_argument",
            "reason": ...}.
        store: Optional store filter. Matched with
            agent.db.get_store_by_name (case-insensitive name or slug). If
            given and no store matches, return {"ok": False, "error":
            "not_found", "reason": ...} naming the store string.
        max_price_usd: Optional inclusive price ceiling. If given and not
            strictly positive, return an "invalid_argument" error.
        limit: Maximum products to return. Clamp to the range
            [1, MAX_SEARCH_LIMIT]; do not error on out-of-range values.

    Returns:
        {"ok": True, "products": [...], "count": <len(products)>} where each
        product is {"product_id": int, "store_id": int, "title": str,
        "price_usd": float}. Sort matches by price_usd ascending, then by
        product_id ascending, and truncate to `limit`. No matches is still a
        success: {"ok": True, "products": [], "count": 0}.

    Implementation notes:
        agent.db.list_products(conn, store_id) gives the candidate set.
        Use `with db.connection() as conn:` to close the database automatically.
    """
    tokens = query.lower().split()
    if not tokens:
        return {
            "ok": False,
            "error": "invalid_argument",
            "reason": "query must not be empty",
        }
    if max_price_usd is not None and max_price_usd <= 0:
        return {
            "ok": False,
            "error": "invalid_argument",
            "reason": f"max_price_usd must be positive, got {max_price_usd}",
        }
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))

    with db.connection() as conn:
        store_id = None
        if store is not None:
            matched = db.get_store_by_name(conn, store)
            if matched is None:
                return {
                    "ok": False,
                    "error": "not_found",
                    "reason": f"no store named {store!r}",
                }
            store_id = matched.id
        candidates = db.list_products(conn, store_id)

    matches = []
    for product in candidates:
        haystack = f"{product.title} {product.description}".lower()
        if not all(token in haystack for token in tokens):
            continue
        if max_price_usd is not None and product.price_usd > max_price_usd:
            continue
        matches.append(
            {
                "product_id": product.id,
                "store_id": product.store_id,
                "title": product.title,
                "price_usd": product.price_usd,
            }
        )

    matches.sort(key=lambda p: (p["price_usd"], p["product_id"]))
    products = matches[:limit]
    return {"ok": True, "products": products, "count": len(products)}


def list_my_orders(ctx: AuthContext) -> dict[str, Any]:
    """List recent orders in the caller's own scope. Risk tier: read.

    Role behavior, straight from the access matrix in SPEC.md:
        - shopper: the caller's own orders.
        - merchant: the caller's store's orders (ctx.store_id).
        - support: support staff have no orders of their own and look up
          specific orders with get_order instead, so return {"ok": False,
          "error": "invalid_argument", "reason": ...} saying exactly that.

    Returns:
        For shopper and merchant: {"ok": True, "orders": [...],
        "count": <len(orders)>} where each order is
        agent.db.Order.to_public_dict() and the list holds at most
        DEFAULT_ORDER_LIMIT orders, newest first (agent.db.list_orders_for_user
        and list_orders_for_store already sort and limit this way).

    Implementation notes:
        No permission check is needed beyond the role dispatch, because the
        scope is baked into which query you run. That is the point of the
        tool: the model cannot ask for someone else's orders through it.
    """
    if ctx.role == "support":
        return {
            "ok": False,
            "error": "invalid_argument",
            "reason": (
                "support staff have no orders of their own; "
                "look up a specific order with get_order"
            ),
        }

    with db.connection() as conn:
        if ctx.role == "merchant":
            orders = db.list_orders_for_store(conn, ctx.store_id)
        else:
            orders = db.list_orders_for_user(conn, ctx.user_id)

    public = [order.to_public_dict() for order in orders[:DEFAULT_ORDER_LIMIT]]
    return {"ok": True, "orders": public, "count": len(public)}


def cancel_order(ctx: AuthContext, order_id: int, reason: str) -> dict[str, Any]:
    """Cancel an order. Risk tier: write.

    This is the homework's write tool, and it must enforce two independent
    rules in this order:

    1. The access matrix (scope): use agent.auth.can_cancel_order. Shoppers
       may cancel only their own orders, merchants only their own store's
       orders, support any order. On failure return
       agent.auth.permission_denied(...) with a reason naming the role and
       the order id. Scope is checked before the status rule so that an
       out-of-scope caller learns nothing about the order's state.
    2. The pre-shipment rule (facts.yaml `cancel_cutoff`): only orders whose
       status is exactly "placed" can be cancelled, for every role. If the
       order is in scope but its status is not "placed", return
       {"ok": False, "error": "not_eligible", "reason": ...} that names the
       current status and states that orders can be cancelled only before
       shipment.

    Args:
        ctx: The caller's auth context.
        order_id: The order to cancel.
        reason: Free-text reason from the user; not validated.

    Returns:
        If no order has this id: {"ok": False, "error": "not_found",
        "reason": ...}.
        On success: {"ok": True, "order_id": order_id, "status": "cancelled"}
        after persisting the new status with agent.db.set_order_status.

    Implementation notes:
        Fetch with agent.db.get_order. Note the argument order of
        can_cancel_order(ctx, order_user_id, order_store_id).

    The Module 4 kill switch is checked first (before the scope and
    status rules and before your code), so that a paused write tool touches
    nothing. It is provided; the default ("off") returns None and falls
    through to your implementation.
    """
    paused = kill_switch("cancel_order")
    if paused is not None:
        return {"ok": False, "error": "paused", "reason": paused}
    with db.connection() as conn:
        order = db.get_order(conn, order_id)
        if order is None:
            return {
                "ok": False,
                "error": "not_found",
                "reason": f"no order with id {order_id}",
            }
        if not can_cancel_order(ctx, order.user_id, order.store_id):
            return permission_denied(
                f"{ctx.role} may not cancel order {order_id}"
            )
        if order.status != "placed":
            return {
                "ok": False,
                "error": "not_eligible",
                "reason": (
                    f"order {order_id} is {order.status}; orders can be "
                    "cancelled only before shipment"
                ),
            }
        db.set_order_status(conn, order_id, "cancelled")

    return {"ok": True, "order_id": order_id, "status": "cancelled"}


def get_store_policy(ctx: AuthContext, store_id: int) -> dict[str, Any]:
    """Look up a store's own policy documents by store id. Risk tier: read.

    Added for Homework 1 Part A ("add more tools of your own"). Store policy
    overrides were only reachable through keyword search: a shopper asking
    about a Juniper Home Goods order sent the agent through repeated
    search_help_center calls before BM25 surfaced the store's doc. A store id
    is already on every order record, so this resolves it directly.

    Store policies are public help-center content, like get_policy, so every
    role may call this and no permission check is needed.

    Args:
        ctx: The caller's auth context. Unused, but every tool takes it.
        store_id: The store to look up, as it appears on an order record.

    Returns:
        On success: {"ok": True, "store_id": int, "store_name": str,
        "return_window_days": int, "platform_return_window_days": int,
        "has_override": bool, "restocking_fee_opt_in": bool,
        "policies": [...]} where each entry is {"policy_id": str,
        "title": str, "audience": str, "body": str}.

        A store with no policy document of its own is still a success:
        "policies" is an empty list, "has_override" is False, and
        "return_window_days" is the platform default. Most stores are in this
        case, and an empty list means "this store publishes no policy of its
        own", not "this store has no return policy".

        If no store has this id: {"ok": False, "error": "not_found",
        "reason": ...} naming the id that was requested.

    Implementation notes:
        The store row carries `return_window_days_override` directly, so the
        effective window does not depend on parsing the policy prose. Policy
        doc ids follow the convention "store-<slug>-policy".
    """
    with db.connection() as conn:
        store = db.get_store(conn, store_id)
    if store is None:
        return {
            "ok": False,
            "error": "not_found",
            "reason": f"no store with id {store_id}",
        }

    prefix = f"store-{store.slug}-"
    policies = [
        {
            "policy_id": doc.policy_id,
            "title": doc.title,
            "audience": doc.audience,
            "body": doc.body,
        }
        for doc in load_policy_docs()
        if doc.policy_id.startswith(prefix)
    ]

    platform_window = load_facts()["return_window_days"]
    override = store.return_window_days_override
    return {
        "ok": True,
        "store_id": store.id,
        "store_name": store.name,
        "return_window_days": override if override is not None else platform_window,
        "platform_return_window_days": platform_window,
        "has_override": override is not None,
        "restocking_fee_opt_in": bool(store.restocking_fee_opt_in),
        "policies": policies,
    }


def find_order(ctx: AuthContext, query: str) -> dict[str, Any]:
    """Search the caller's orders by product name. Risk tier: read.

    Takes a natural-language query (e.g., "earmuffs I bought last week")
    and searches the authenticated user's orders for products whose name
    matches. Use fuzzy string matching (e.g., thefuzz.fuzz.partial_ratio
    or case-insensitive substring matching) to find orders whose product name is close to the
    query.

    Access rules: a shopper searches only the shopper's own orders, a
    merchant searches orders from the merchant's store, and support staff
    can search any orders. Use agent.db.list_order_search_candidates with
    user_id=ctx.user_id for shoppers, store_id=ctx.store_id for merchants,
    or all_orders=True only for support. Derive the scope from ctx, never
    from the query; reject unsupported roles or missing required identity.
    Use agent.db.list_products to map product IDs to product titles.

    The helper returns the complete authorised scope, newest first with
    order ID descending as the tie-breaker. Match product names first,
    preserve that order, then return at most five matches. Do not search
    only the 20 most recent orders. Convert matches with to_public_dict().

    Args:
        ctx: The caller's auth context.
        query: A natural-language description of the product.

    Returns:
        {"ok": True, "orders": [...]} with a list of matching orders
        (at most 5), each as the dict returned by agent.db. If no orders
        match, return {"ok": True, "orders": []}.
    """
    if not query.strip():
        return {"ok": True, "orders": []}

    with db.connection() as conn:
        if ctx.role == "shopper":
            orders = db.list_orders_for_user(conn, ctx.user_id)
        elif ctx.role == "merchant":
            orders = db.list_orders_for_store(conn, ctx.store_id)
        else:  # support: any order
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY ordered_at DESC, id DESC LIMIT ?",
                (DEFAULT_ORDER_LIMIT,),
            ).fetchall()
            orders = [db._order_from_row(row) for row in rows]
        titles = {product.id: product.title for product in db.list_products(conn)}

    scored = []
    for order in orders:
        title = titles.get(order.product_id, "")
        score = _title_match_score(query, title)
        if score >= FIND_ORDER_MIN_SCORE:
            record = order.to_public_dict()
            record["product_title"] = title
            record["match_score"] = round(score, 1)
            scored.append(record)

    scored.sort(key=lambda o: (-o["match_score"], o["order_id"]))
    return {"ok": True, "orders": scored[:FIND_ORDER_MAX_RESULTS]}
