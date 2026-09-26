-- V15: Chống chỉ định (contraindications) cho mục checklist theo tag khảo sát cá nhân hóa.
--
-- Mỗi mục checklist (care_item_templates.entry_type = 'CHECKLIST_ENTRY') có thể khai báo
--   configuration_jsonb.contraindications = ["<TAG>", ...]
-- với TAG là mã trong questionnaire của mẹ (recommendation_questionnaire.dart). Backend ẩn mục
-- khỏi Trang chủ / Lộ trình / Chia sẻ cho chuyên gia khi hồ sơ khảo sát hiện tại của mẹ chứa
-- tag trùng, và mục ẩn không chặn việc hoàn thành checklist. Không cần cột mới.
--
-- Nguyên tắc gắn tag (an toàn):
--   * Chỉ gắn cho hướng dẫn tự chăm sóc chung mà chính nội dung có thể gây hại cho nhóm bệnh
--     (cường độ vận động, bổ sung vi chất liều cố định, vắc-xin sống).
--   * KHÔNG gắn cho sàng lọc, đo/theo dõi chỉ số, khám, tư vấn, hay mục chứa dấu hiệu cảnh báo
--     cần dừng/đi viện: nhóm bệnh nền càng cần các mục này.
--
-- Căn cứ:
--   [ACOG-804] ACOG Committee Opinion No. 804 (2020), Physical Activity and Exercise During
--              Pregnancy and the Postpartum Period — chống chỉ định tuyệt đối/tương đối.
--   [ACIP]     CDC/ACIP General Best Practice Guidelines for Immunization — Contraindications
--              and Precautions: vắc-xin sống (MMR, thủy đậu) chống chỉ định khi suy giảm miễn dịch
--              nặng / đang điều trị ức chế miễn dịch.
--   [WHO-IFA]  WHO Guideline: Daily iron and folic acid supplementation in pregnant women (2012)
--              và WHO Guideline on haemoglobin cutoffs / iron (2024): thiếu máu cần xác định
--              nguyên nhân (thiếu sắt vs bệnh huyết sắc tố như thalassemia) và điều trị theo liều
--              riêng; bổ sung sắt khi không thiếu sắt có thể gây quá tải sắt.
--   [AHA-2021] AHA Scientific Statement: Cardiovascular considerations in caring for pregnant
--              patients (2020/2021) — bệnh tim cần bác sĩ tim mạch cá thể hóa mức vận động.
--
-- Mục được khớp theo (stage, tên checklist, tên mục) trên mọi phiên bản, vì task cũ vẫn tham
-- chiếu phiên bản mục cũ. Mục không tồn tại trong DB thì câu lệnh không có hiệu lực.
-- Guard trigger bất biến của phiên bản APPROVED được bỏ qua bằng vai trò MIGRATION (chỉ trong
-- transaction này), giống các migration checklist trước đây.

SET LOCAL carebridge.checklist_p1_p2_role = 'MIGRATION';

WITH mapping(stage, checklist_title, item_title, tags) AS (
    VALUES
    -- PRE_PREG_03 #3. [AHA-2021] Bệnh tim: chương trình tập luyện phải do bác sĩ tim mạch
    -- chỉ định (đánh giá chức năng tim, NYHA) trước khi áp dụng khuyến nghị tập đều đặn chung.
    ('PRE_PREGNANCY', 'Điều chỉnh dinh dưỡng và lối sống',
     'Tập thể dục thường xuyên, nghỉ ngơi hợp lý',
     '["CARDIOVASCULAR_DISEASE"]'::jsonb),

    -- PRE_PREG_04 #1. [WHO-IFA] Liều sắt 30–60 mg/ngày dùng chung không phù hợp khi đã thiếu
    -- máu: thiếu máu thiếu sắt cần liều điều trị, thalassemia (phổ biến ở Việt Nam) không được
    -- bổ sung sắt nếu không thiếu sắt. Bác sĩ chỉ định phác đồ riêng.
    ('PRE_PREGNANCY', 'Bổ sung vi chất & hoàn thành tiêm chủng',
     'Bổ sung Sắt và Axit Folic trước thai kỳ',
     '["ANEMIA"]'::jsonb),

    -- PRE_PREG_04 #5. [ACIP] MMR và thủy đậu là vắc-xin sống: chống chỉ định khi suy giảm miễn
    -- dịch nặng / đang dùng thuốc ức chế miễn dịch (thường gặp ở Lupus và bệnh tự miễn).
    -- Mục rà soát tiêm chủng chung (vắc-xin bất hoạt) vẫn hiển thị.
    ('PRE_PREGNANCY', 'Bổ sung vi chất & hoàn thành tiêm chủng',
     'Tuân thủ khoảng cách sau tiêm MMR và thủy đậu',
     '["LUPUS", "AUTOIMMUNE_DISEASE"]'::jsonb),

    -- PREG_DAILY_03 #2. [ACOG-804] Chống chỉ định tuyệt đối: bệnh tim có ý nghĩa huyết động,
    -- tiền sản giật/tăng huyết áp thai kỳ, nguy cơ chuyển dạ sinh non (hở eo tử cung, khâu
    -- vòng cổ tử cung); tương đối: tăng huyết áp kiểm soát kém. Tiền sử sinh non là yếu tố nguy
    -- cơ chính của sinh non tái phát → cần đánh giá cổ tử cung trước khi vận động vừa sức.
    -- Các mục hít thở, Kegel, giãn cơ nhẹ và mục "Uống đủ nước và theo dõi dấu hiệu" (chứa dấu
    -- hiệu phải ngừng tập) vẫn hiển thị.
    ('PREGNANCY', 'Vận động nhẹ nhàng & giãn cơ hàng ngày cho mẹ bầu',
     'Đi bộ nhẹ nhàng hoặc bài tập vận động vừa sức (15–20 phút)',
     '["CARDIOVASCULAR_DISEASE", "HYPERTENSION", "PRIOR_PRETERM_BIRTH"]'::jsonb)
)
UPDATE public.care_item_templates AS item
SET configuration_jsonb = COALESCE(item.configuration_jsonb, '{}'::jsonb)
        || jsonb_build_object('contraindications', mapping.tags)
FROM mapping, public.care_item_templates AS root
WHERE item.entry_type = 'CHECKLIST_ENTRY'
  AND root.template_id = item.parent_template_id
  AND root.entry_type = 'TEMPLATE_ROOT'
  AND root.stage = mapping.stage
  AND root.title = mapping.checklist_title
  AND item.title = mapping.item_title;
