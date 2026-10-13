# Nordlys Home — Returns and Refunds Policy (fictional teaching case)

All amounts are in EUR. Day counts are calendar days.

**R1 Standard return.** An unused item may be returned for a full refund to the original payment method within 30 days of the delivery date (day 30 is still eligible).

**R2 Final-sale items.** Items marked `final_sale` cannot be returned for a change of mind. The only exception is R4 (damaged or defective on arrival).

**R3 Late returns.** From day 31 to day 45 after delivery, the customer may return an unused item for store credit only (no cash refund). After day 45, returns are refused.

**R4 Damaged or defective on arrival.** This covers an item that was broken when delivered, or a product that does not work. If the customer reports the problem within 14 days of delivery and provides a photo, the item is refunded in full, final-sale items included. Without a photo, ask for one. After 14 days, a manager decides.

**R5 Cancellation.** An order with status `processing` can be cancelled for a full refund. An order with status `shipped` cannot be cancelled; the customer may return it after delivery under R1–R3.

**R6 Late delivery.** An order with status `shipped` that is 10 days or fewer past its estimated delivery date is not yet eligible for a refund; explain that it is still in transit. More than 10 days past the estimated delivery date, a manager opens a lost-parcel investigation.

**R7 Manager approval for large refunds.** Any refund above 100 EUR requires manager approval. The support agent must not approve it alone.

**R8 Identity check.** The sender's email must match the email on the order. If the order cannot be found for this sender, ask the customer for the correct order number and the email used at checkout. Never reveal order details to a sender who does not match.

**R9 Exceptions.** If the customer explicitly asks for an exception to this policy, a manager decides. This takes precedence over a refusal under R2 or R3 (but not over the identity check R8). Never promise an exception, a refund or a delivery time that the policy or the order record does not support.

**Refund amount.** The refund equals the price of the returned item(s). A cancellation refunds the whole order. Shipping fees are out of scope for this pilot.

**Information not covered.** This policy says nothing about shipping times, delivery fees or stock. Do not invent them; tell the customer a team member will follow up.

## Decision labels

- `approve_refund`: eligible for a cash refund of at most 100 EUR.
- `store_credit`: eligible for store credit only (R3).
- `reject`: not eligible under the policy, or not yet eligible (for example R6, parcel still in transit).
- `ask_info`: a required fact or photo is missing, or the identity check failed.
- `escalate`: a manager must decide (R4 after day 14, R6 lost parcel, R7, R9).

Every draft reply is reviewed by a staff member before it is sent. Nothing is sent automatically.
