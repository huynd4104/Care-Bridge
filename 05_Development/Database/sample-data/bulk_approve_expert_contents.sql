-- ============================================================================
-- CareBridge: Kịch bản SQL duyệt hàng loạt nội dung cần thẩm định của Expert
-- Áp dụng cho:
--   1. public.content_items (Bài viết y tế ARTICLE, Câu hỏi thường gặp FAQ)
--   2. public.care_item_templates (Checklist mẫu hành trình sức khỏe)
-- ============================================================================

-- BƯỚC 1: KIỂM TRA CÁC NỘI DUNG ĐANG CHỜ EXPERT THẨM ĐỊNH (PENDING_REVIEW)
-- ----------------------------------------------------------------------------
-- 1.1. Danh sách bài viết & FAQ chờ thẩm định
SELECT 
    ci.content_item_id,
    ci.content_type,
    ci.title,
    ci.stage,
    ci.status,
    ci.assigned_expert_id,
    u.full_name AS assigned_expert_name,
    u.email AS assigned_expert_email,
    ci.created_at
FROM public.content_items ci
LEFT JOIN public.users u ON u.user_id = ci.assigned_expert_id
WHERE ci.status = 'PENDING_REVIEW'
ORDER BY ci.created_at DESC;

-- 1.2. Danh sách Checklist mẫu chờ thẩm định
SELECT 
    ct.template_id,
    ct.title,
    ct.stage,
    ct.template_type,
    ct.content_status,
    ct.assigned_expert_id,
    u.full_name AS assigned_expert_name,
    u.email AS assigned_expert_email,
    ct.created_at
FROM public.care_item_templates ct
LEFT JOIN public.users u ON u.user_id = ct.assigned_expert_id
WHERE ct.entry_type = 'TEMPLATE_ROOT' 
  AND ct.content_status = 'PENDING_REVIEW'
ORDER BY ct.created_at DESC;


-- BƯỚC 2: DUYỆT HÀNG LOẠT TRONG DATABASE (TRANSACTION AN TOÀN)
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    v_default_expert_id UUID;
    v_content_count INT := 0;
    v_checklist_count INT := 0;
BEGIN
    -- Lấy ID chuyên gia mặc định nếu bản ghi chưa được gán chuyên gia cụ thể
    SELECT user_id INTO v_default_expert_id 
    FROM public.users 
    WHERE email = 'expert@carebridge.dev' 
    LIMIT 1;

    -- Nếu không tìm thấy expert@carebridge.dev thì lấy bất kỳ user nào có role EXPERT
    IF v_default_expert_id IS NULL THEN
        SELECT u.user_id INTO v_default_expert_id
        FROM public.users u
        JOIN public.user_roles ur ON ur.user_id = u.user_id
        JOIN public.roles r ON r.role_id = ur.role_id
        WHERE r.name = 'EXPERT'
        LIMIT 1;
    END IF;

    -- 2.1. DUYỆT HÀNG LOẠT BÀI VIẾT & FAQ (content_items)
    WITH updated_items AS (
        UPDATE public.content_items
        SET 
            status = 'APPROVED',
            approved_by = COALESCE(assigned_expert_id, v_default_expert_id),
            approved_at = NOW(),
            published_at = COALESCE(published_at, NOW()),
            revision_reason = NULL,
            revision_requested_at = NULL,
            revision_requested_by = NULL,
            revision_requested_version = NULL,
            updated_at = NOW()
        WHERE status = 'PENDING_REVIEW'
        RETURNING content_item_id
    )
    SELECT count(*) INTO v_content_count FROM updated_items;

    -- 2.2. DUYỆT HÀNG LOẠT CHECKLIST MẪU (care_item_templates)
    WITH updated_checklists AS (
        UPDATE public.care_item_templates
        SET 
            content_status = 'APPROVED',
            approved_by = COALESCE(assigned_expert_id, v_default_expert_id),
            approved_at = NOW(),
            distribution_enabled = (template_type = 'MANDATORY'),
            migration_review_required = false,
            revision_reason = NULL,
            revision_requested_at = NULL,
            revision_requested_by = NULL,
            revision_requested_version = NULL,
            updated_at = NOW()
        WHERE entry_type = 'TEMPLATE_ROOT' 
          AND content_status = 'PENDING_REVIEW'
        RETURNING template_id
    )
    SELECT count(*) INTO v_checklist_count FROM updated_checklists;

    RAISE NOTICE 'Đã duyệt thành công: % bài viết/FAQ và % checklist templates.', v_content_count, v_checklist_count;
END $$;


-- BƯỚC 3: KIỂM TRA LẠI KẾT QUẢ SAU KHI DUYỆT
-- ----------------------------------------------------------------------------
-- 3.1. Thống kê số lượng nội dung theo trạng thái
SELECT 'content_items' AS entity, status, count(*) 
FROM public.content_items 
GROUP BY status
UNION ALL
SELECT 'care_item_templates' AS entity, content_status AS status, count(*) 
FROM public.care_item_templates 
WHERE entry_type = 'TEMPLATE_ROOT'
GROUP BY content_status;

-- 3.2. Xem các nội dung vừa được duyệt gần nhất
SELECT 
    'CONTENT' AS kind,
    ci.title,
    ci.content_type AS type,
    ci.status,
    u.full_name AS approved_by_name,
    ci.approved_at
FROM public.content_items ci
LEFT JOIN public.users u ON u.user_id = ci.approved_by
WHERE ci.approved_at >= NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
    'CHECKLIST' AS kind,
    ct.title,
    'CHECKLIST' AS type,
    ct.content_status AS status,
    u.full_name AS approved_by_name,
    ct.approved_at
FROM public.care_item_templates ct
LEFT JOIN public.users u ON u.user_id = ct.approved_by
WHERE ct.entry_type = 'TEMPLATE_ROOT' 
  AND ct.approved_at >= NOW() - INTERVAL '1 hour'
ORDER BY approved_at DESC;
