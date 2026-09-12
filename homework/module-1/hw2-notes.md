# HW2 notes

Working notes for Homework 2.

## Part E, traced requests


## Part F, prompt version comparison

Request used: record 1, shopper 1, "What is the status of order 4127?"

| Run | Prompt | Trace id | prompt_version | Note |
| --- | --- | --- | --- | --- |
| A | new (ESC-2 wording) | 1c43d7b67056 | This shows up in first ~6 traces in langfuse | |
| B | old (HW1 pre-edit wording) | | 0811eb545d28 | |

###Wording difference (new first, then old)
```
 ## Escalation
-When you are unsure, an action is above your authority (for example a
-refund above the auto-approval threshold), or the user asks for an account
-change such as an email address update, call escalate_to_human and tell
-the user a human will follow up.
+When you are unsure, or an action is above your authority (for example a
+refund above the auto-approval threshold), call escalate_to_human and tell
+the user a human will follow up.
```

## Trace record candidates 

See hw2-traces.json

Video is at https://www.loom.com/share/2e1986b24dcf414dbf22e6ab256941b3


