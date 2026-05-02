# Execution Guard

No order can reach MT5 unless the Execution Guard approves it and issues a short-lived approval token.

The Execution Agent must call the guard; the MT5 bridge independently validates the token and still requires `order_check` before `order_send`.
