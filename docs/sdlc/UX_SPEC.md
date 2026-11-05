# UX Specification — MealMate Consumer Experience (P1 Proposal)

**Version:** 0.1 | **Status:** PROPOSED, NOT an approved frontend build spec. This document defines expected user behavior and accessibility for design review after the verified API path.

## Experience principles

- **Useful before beautiful:** chat helps interpret user needs; numeric ingredient and cart data are sourced, reviewable facts.
- **One current draft:** show its revision, selected store and expiry context; no invisible acceptance or checkout.
- **Clarity of uncertainty:** separate price/stock cart verification from per-allergen evidence and user approval.
- **Editable controls:** user can inspect and deliberately apply portion/budget/pantry/dish changes. A hypothetical never acts as an edit.
- **Vietnamese-first:** money in VND, canonical quantity units clearly displayed, plain language source warnings.

## Information architecture

1. **Chat + constraints:** user request, current diners, meal type, budget, dislikes, declared allergens, dietary restrictions, pantry entries and confidence/clarification needs.
2. **Menu:** sourced recipes, role (main/side/shared), version, number of portions, source rationale, edit action.
3. **Ingredient resolution:** required, confirmed available, to buy; measurement unit and conversion warning.
4. **Retail cart:** store and snapshot, each selected SKU, pack quantity/size, pack count, leftover, current price, source and subtotal; explicit tax/shipping/promotion exclusion.
5. **Verification/approval:** cart-data status, meal-allergen status, review state, exact blockers or pantry-only warnings, explicit “Chấp nhận giỏ hàng nháp” action.

**Desktop proposal:** chat/constraints on left; stacked menu and ingredient/cart review on right. **Mobile proposal:** chat and separate review tabs with persistent status context. These are UX design recommendations, not implementation approvals or pixel specifications.

## Interaction contract

| Interaction | Expected state effect | UI response |
| --- | --- | --- |
| Initial meal prompt | Interpret constraints, clarify essential data; create DRAFT only on feasible sourced plan | Menu and sourced cart, or precise next question |
| Explain “Vì sao chọn món này?” | **No** request/draft revision change | Explain using recipe/source rationale |
| Hypothetical “Nếu tăng rau?” | **No** mutation | Show it as comparison/provisional explanation, not committed cart |
| Apply “Tăng rau từ 4 lên 6 phần” | Increment material request revision and reverify new DRAFT | Updated portions, quantity and subtotal; old approval invalid |
| Change SKU/menu | Explicit material edit, maintain all unmentioned constraints | New scoped verification and warnings |
| Select accepted draft and edit | Preserve accepted record, create separate new draft ID | Indicate “giỏ mới chưa được chấp nhận” |
| Click accept | Send expected cart revision through dedicated acceptance endpoint | ACCEPTED, RECONFIRM_REQUIRED or BLOCKED with reasons; never “Đã đặt hàng” |
| Price/stock expired | Current acceptance invalid; ask to refresh/reconfirm | Show expired fact and refreshed source if available |
| Pantry-only allergy UNKNOWN | May enable explicit acceptance **only** when all non-pantry gates pass and warning remains visible | Prominent specific pantry warning without “an toàn” wording |
| Purchased-SKU/recipe evidence UNKNOWN | Block acceptance | Exact SKU/component + allergen/evidence missing, suggest sourced alternative |
| No candidate under bounded search | No proposed acceptable cart | Show evaluated blockers and invitation for user-controlled changes |
| Delete session | Remove user session/drafts | Confirm deletion, prevent stale URL reuse |

## Wireframe (conceptual, not visual approval)

~~~text
MealMate | Bữa tối 4 người | Ngân sách 140.000đ | Siêu thị FG-01
[Chat conversation]                   [Thực đơn: 3 món | sửa số phần]
[Giải thích / thử phương án]           [Nguyên liệu: cần / sẵn có / phải mua]
[Thông tin cần xác nhận...]            [SKU: 5 dòng / 6 gói / dư mỗi gói]
                                      [Tạm tính 116.000đ — ảnh chụp S-FG-001]
                                      [Trạng thái giỏ] [Đánh giá dị ứng]
                                      [Cảnh báo / blocker có nguồn]
                                      [Chấp nhận giỏ hàng nháp]
                                      [Không phải đặt hàng hoặc thanh toán]
~~~

Fixture amounts above are **synthetic illustration**, not actual store pricing.

## State-aware content language

| Domain state | Proposed wording |
| --- | --- |
| VERIFIED | “Giá, số gói và tồn kho của giỏ đã được kiểm tra theo nguồn được ghi nhận.” |
| NOT_ASSESSED | “Chưa đánh giá dị ứng vì chưa khai báo dị nguyên.” |
| REVIEW_REQUIRED, pantry-only | “Thiếu thông tin dị ứng cho nguyên liệu đang có ở nhà: [item]. Điều này không xác nhận món ăn an toàn.” |
| REVIEW_REQUIRED, selected SKU | “Không thể chấp nhận giỏ này: thiếu đánh giá [allergen] cho [SKU].” |
| RECONFIRM_REQUIRED | “Dữ liệu đã thay đổi hoặc hết hiệu lực. Vui lòng xem và xác nhận giỏ mới.” |
| Bounded exhausted | “Trong 3 phương án đã kiểm tra chưa tìm được giỏ đủ điều kiện; không có nghĩa mọi phương án đều không thể.” |
| ACCEPTED | “Đã chấp nhận giỏ hàng nháp. Chưa đặt hàng và chưa thanh toán.” |

Do not say: “100% an toàn”, “không gây dị ứng”, “giá checkout cuối cùng”, “đã mua hàng”.

## Accessibility and error states

Every form field has a label, validation guidance and keyboard focus order. Status is conveyed by text+icon, not color alone. Important warning remains perceivable at approval; no hidden accordion-only critical blocker. Use accessible dialog semantics for review confirmation; prevent duplicate acceptance by disabling UI on in-flight action **and** relying on backend CAS. Test loading, timeout, offline, empty recipes, source unavailable, invalid inputs, stale revision, expired session and data with long dish names.

## UX acceptance (future)

Human review of low-fidelity flows; keyboard and screen-reader pass; explicit acceptance copy; error accessibility and 3 distinct statuses; no fabricated provider output. **No frontend coding until a separately reviewed UX/tech plan is authorized.**
