---
title: "WHO Digital Adaptation Kit cho chăm sóc trước sinh: yêu cầu vận hành hệ thống số"
stage: PREGNANCY
topic: HEALTH_MONITORING
document_type: HANDBOOK
source: "Digital adaptation kit for antenatal care: operational requirements for implementing WHO recommendations in digital systems"
organization: "World Health Organization"
section: "SMART Guidelines / Digital tracking and decision support for ANC"
publication_year: 2021
language: vi
source_language: en
source_file: "Digital_adaptation_kit_for_antenatal_care_operational_requirements_for_implementing_WHO_recommendations_in_dig.pdf"
source_drive_id: "1sX4LU2vyuGl8-igITmiwnPOy0zxgfIZy"
context_scope: "Khung vận hành số mang tính tổng quát; phải điều chỉnh theo chính sách, phạm vi hành nghề và hạ tầng của từng quốc gia/cơ sở"
clinical_authority_note: "Tài liệu này đóng gói yêu cầu vận hành số dựa trên các hướng dẫn WHO; không thay thế guideline lâm sàng gốc."
---

# WHO Digital Adaptation Kit cho chăm sóc trước sinh

## Phạm vi và mục tiêu

### DAK là gì?
Digital Adaptation Kit (DAK) cho chăm sóc trước sinh (ANC — antenatal care, chăm sóc trước sinh) là tài liệu vận hành giúp chuyển các khuyến nghị WHO thành yêu cầu có thể triển khai trong hệ thống số theo hướng SMART Guidelines. DAK không phải là một guideline lâm sàng mới. Nó cung cấp ngôn ngữ chung cho cán bộ chương trình sức khỏe bà mẹ, nhóm hệ thống thông tin, nhà phân tích nghiệp vụ và nhóm phát triển phần mềm để cùng hiểu nội dung y tế cần được thể hiện trong hệ thống theo dõi số và hỗ trợ quyết định.

### Mục tiêu của DAK ANC
- Bảo đảm nội dung trong hệ thống số bám theo guideline lâm sàng, sức khỏe cộng đồng và sử dụng dữ liệu của WHO.
- Giúp nhóm chuyên môn y tế và nhóm kỹ thuật cùng rà soát được tính hợp lệ, chính xác và đầy đủ của nội dung y tế.
- Cung cấp điểm khởi đầu cho bộ dữ liệu cốt lõi, luồng công việc và logic hỗ trợ quyết định trong hệ thống ANC.
- Hỗ trợ theo dõi dọc một phụ nữ mang thai qua nhiều lần tiếp xúc, nhắc lịch, quản lý chuyển tuyến và dùng lại dữ liệu đã thu cho báo cáo/chỉ số.

### Nguyên tắc điều chỉnh theo bối cảnh
DAK cố ý được xây dựng ở mức tổng quát. Trước khi triển khai, từng quốc gia hoặc cơ sở phải điều chỉnh theo chính sách quốc gia, mô hình cung ứng dịch vụ, phạm vi hành nghề của từng nhóm nhân viên y tế, ngôn ngữ, hạ tầng điện–mạng, tuyến chuyển viện, danh mục xét nghiệm/thuốc có sẵn và quy định bảo mật. Không được coi các persona, workflow hoặc trigger trong DAK là cấu hình bắt buộc giống nhau cho mọi nơi.

## Tám thành phần cốt lõi của DAK

### Thành phần 1 — Can thiệp y tế và khuyến nghị
DAK tập trung vào các can thiệp ANC cốt lõi trong danh mục bao phủ y tế toàn dân của WHO: giáo dục sức khỏe và tư vấn để thúc đẩy thai kỳ khỏe mạnh; bổ sung dinh dưỡng trong thai kỳ; đánh giá và sàng lọc mẹ và thai; biện pháp dự phòng và tiêm chủng; xử trí các triệu chứng sinh lý thường gặp trong thai kỳ; và mô hình ANC có tối thiểu tám lần tiếp xúc. Nội dung này lấy từ WHO ANC 2016 và các hướng dẫn WHO liên quan, không tự tạo ra khuyến nghị mới.

### Thành phần 2 — Persona tổng quát
Nhóm người dùng mục tiêu chính gồm hộ sinh phụ trợ, điều dưỡng và hộ sinh có năng lực cung cấp các can thiệp thiết yếu trong ANC. Persona liên quan gồm phụ nữ mang thai, nhân viên y tế cộng đồng (CHW — community health worker), người giám sát điều dưỡng/hộ sinh, cán bộ quản lý cơ sở và bác sĩ chuyên khoa khi cần. Khi triển khai, persona phải được điều chỉnh theo chức danh, trách nhiệm, năng lực số, môi trường làm việc, khoảng cách chuyển tuyến và điều kiện Internet thực tế.

### Thành phần 3 — Kịch bản người dùng
Kịch bản người dùng mô tả cách các persona tương tác trong những tình huống điển hình như đăng ký lần đầu, xác nhận thai, khai thác bệnh sử, đo huyết áp, chỉ định xét nghiệm, tư vấn, phát hiện dấu hiệu nguy hiểm, chuyển tuyến và đặt lịch lần khám tiếp theo. Các kịch bản chỉ nhằm làm rõ luồng sử dụng hệ thống; không phải một quy trình cứng áp dụng cho mọi cơ sở.

### Thành phần 4 — Quy trình nghiệp vụ và workflow
Quy trình nghiệp vụ mô tả tập hợp hoạt động cần thực hiện để đạt mục tiêu chăm sóc, ví dụ đăng ký, cung cấp ANC, chuyển tuyến và theo dõi tại cộng đồng. Workflow thể hiện thứ tự hoạt động, điểm quyết định và tương tác giữa người dùng. Khi chuyển sang RAG hoặc hệ thống hỗ trợ quyết định, các sơ đồ được biểu diễn lại dưới dạng logic tuần tự và If–Then để tránh mất ngữ cảnh khi chunking.

### Thành phần 5 — Dữ liệu cốt lõi
Bộ dữ liệu cốt lõi gồm các trường cần thu tại từng điểm trong workflow để hỗ trợ chăm sóc, ra quyết định và tính chỉ số. DAK định hướng ánh xạ dữ liệu sang các chuẩn thuật ngữ như ICD và SNOMED để tăng khả năng tương tác giữa các hệ thống. Triển khai địa phương có thể thêm trường dữ liệu nhưng cần duy trì định nghĩa, kiểu dữ liệu, đơn vị và nguồn gốc rõ ràng.

### Thành phần 6 — Logic hỗ trợ quyết định
Logic hỗ trợ quyết định tách guideline thành các đầu vào, điều kiện, đầu ra và hành động. Cấu trúc ưu tiên dạng If–Then: nếu một hoặc nhiều điều kiện đầu vào thỏa mãn, hệ thống sinh chẩn đoán/flag/cảnh báo hoặc yêu cầu hành động tương ứng như xét nghiệm, điều trị, tư vấn hay chuyển tuyến. Logic số không mở rộng phạm vi hành nghề: hệ thống chỉ nên hỗ trợ các nhiệm vụ vốn đã nằm trong phạm vi công việc của người dùng.

### Thành phần 7 — Chỉ số và chỉ số hiệu suất
Hệ thống cần có bộ chỉ số có thể tính từ dữ liệu thường quy, với tử số, mẫu số và phân tầng rõ ràng. DAK nhấn mạnh nguyên tắc “collect once, use many”: dữ liệu nhập để chăm sóc cá thể có thể được dùng tiếp cho giám sát, chất lượng dịch vụ và báo cáo quản lý khi phù hợp. Việc tính chỉ số phải dựa trên định nghĩa chuẩn và có khả năng kiểm tra ngược dữ liệu nguồn.

### Thành phần 8 — Yêu cầu chức năng và phi chức năng
Yêu cầu chức năng mô tả hệ thống phải làm được gì trong từng workflow. Yêu cầu phi chức năng mô tả các thuộc tính như bảo mật, phân quyền, audit log, khả năng làm việc offline, phục hồi sau mất điện/mạng, sao lưu, đa ngôn ngữ, tính dễ dùng và khả năng hoạt động trên màn hình nhỏ. Các yêu cầu này cần được điều chỉnh theo nguồn lực và nhu cầu thực tế.

## Workflow ANC dạng văn bản

### Đăng ký và nhận diện người bệnh
- Nếu người phụ nữ đến cơ sở và có dấu hiệu cấp cứu, cho phép bỏ qua luồng đăng ký chuẩn để chuyển ngay sang đánh giá nhanh và xử trí.
- Nếu không cấp cứu, tìm hồ sơ bằng ít nhất hai yếu tố nhận diện trước khi tạo hồ sơ mới nhằm giảm trùng lặp.
- Nếu chưa xác định đầy đủ danh tính trong tình huống cấp cứu, hệ thống có thể cho phép tạo định danh tạm thời.
- Mọi lần tiếp xúc nên có dấu thời gian; thay đổi thông tin nhân khẩu học cần lưu lịch sử chỉnh sửa.

### Luồng tiếp xúc ANC
1. Đăng ký hoặc xác nhận hồ sơ hiện có.
2. Thực hiện Rapid Assessment and Management (RAM — đánh giá và xử trí nhanh).
3. Nếu có dấu hiệu nguy hiểm cần chuyển tuyến → chuyển sang luồng referral ngay.
4. Nếu không có dấu hiệu nguy hiểm → xác nhận tình trạng mang thai khi cần.
5. Xác định đây là lần tiếp xúc đầu tiên hay lần theo dõi.
6. Nếu lần đầu → thu hồ sơ thai kỳ, bệnh sử, tiền sử sản khoa, thuốc đang dùng, hành vi, tiêm chủng và thông tin nền.
7. Nếu tái khám → rà lại triệu chứng, hành vi, thuốc và vấn đề đã ghi nhận trước đó.
8. Khám lâm sàng, đánh giá mẹ và thai.
9. Chỉ định hoặc rà kết quả xét nghiệm và hình ảnh học; giải thích cho người phụ nữ về các xét nghiệm được chỉ định.
10. Tư vấn, xử trí tại cơ sở và điều trị phù hợp với dữ liệu đã thu.
11. Nếu phát hiện vấn đề vượt khả năng cơ sở → chuyển tuyến.
12. Nếu không cần chuyển tuyến → đặt lịch lần tiếp xúc tiếp theo.
13. Hướng dẫn tự chăm sóc/tự theo dõi tại nhà hoặc cộng đồng và nhắc dấu hiệu cần liên hệ cơ sở ngay.

### Nội dung tư vấn và xử trí trong ANC
Workflow DAK gom các chủ đề thành nhóm: giảm caffeine, cai thuốc lá và tránh khói thuốc thụ động, sử dụng bao cao su, rượu/chất gây nghiện; buồn nôn/nôn, ợ nóng, táo bón, đau lưng/chậu, giãn tĩnh mạch, phù; dinh dưỡng và vận động; tăng huyết áp/tiền sản giật; HIV, viêm gan B/C, giang mai, lao; nhiễm khuẩn niệu không triệu chứng; đái tháo đường trong thai kỳ; thiếu máu; nguy cơ HIV; lịch tiếp xúc ANC; kế hoạch sinh; kế hoạch hóa gia đình sau sinh; nuôi con bằng sữa mẹ; dự phòng thiếu máu, tẩy giun, sốt rét và tiêm chủng theo bối cảnh.

## Dấu hiệu nguy hiểm và RAM

### Logic If–Then cho dấu hiệu nguy hiểm
Nếu người phụ nữ có một trong các biểu hiện sau, hệ thống phải đưa khỏi luồng chăm sóc thường quy và kích hoạt RAM: bất tỉnh; co giật; chảy máu âm đạo; đau bụng dữ dội; trông rất bệnh; đau đầu kèm rối loạn thị giác; khó thở nặng; tím trung tâm; sốt; nôn dữ dội; đau dữ dội; sắp sinh; hoặc đang chuyển dạ. Hành động đi kèm trong DAK: chuyển ngay tới khu đánh giá/xử trí nhanh, gọi hỗ trợ, trấn an rằng sẽ được chăm sóc ngay và cho người đi cùng ở lại khi phù hợp.

### Không có dấu hiệu nguy hiểm
Nếu không có dấu hiệu nguy hiểm ở quick check/RAM, người phụ nữ có thể tiếp tục luồng ANC thường quy. Hệ thống vẫn phải cho phép kích hoạt chuyển tuyến cấp cứu ở bất kỳ thời điểm nào nếu dấu hiệu nguy hiểm xuất hiện trong quá trình khám, tư vấn hoặc nhập dữ liệu.

## Chuyển tuyến ANC

### Chuyển tuyến cấp cứu
- Nếu cần chuyển tuyến cấp cứu → ổn định người phụ nữ và thực hiện điều trị trước chuyển tuyến cần thiết.
- Nếu chưa ổn định để vận chuyển → tiếp tục xử trí ổn định trước khi di chuyển.
- Khi đủ ổn định → tổ chức vận chuyển cấp cứu.
- Liên hệ cơ sở nhận nếu có thể và chuyển kèm thông tin lâm sàng, nhân khẩu học, nhận diện và xử trí đã thực hiện.

### Chuyển tuyến không cấp cứu hoặc chuyển tuyến theo năng lực
Nếu cơ sở không có dịch vụ/năng lực cần thiết hoặc có yếu tố nguy cơ cần mức chăm sóc cao hơn, thảo luận với người phụ nữ và gia đình về cơ sở phù hợp, cách di chuyển, người cần gặp và những gì dự kiến sẽ diễn ra. Cơ sở gửi nên xác nhận nơi nhận có khả năng tiếp nhận; nếu không, chọn cơ sở khác phù hợp. Hệ thống số có thể hỗ trợ biểu mẫu referral và truyền dữ liệu nếu hạ tầng cho phép.

## Theo dõi ANC tại cộng đồng

### Luồng CHW
Nhân viên y tế cộng đồng có thể lập kế hoạch thăm hoặc ngày cộng đồng, thực hiện quick check, đánh giá hỗ trợ gia đình/xã hội và xác định dấu hiệu nguy hiểm. Nếu có dấu hiệu cần chuyển tuyến → thực hiện referral. Nếu không → tư vấn các hành vi, triệu chứng sinh lý, dinh dưỡng, lịch ANC, kế hoạch sinh, kế hoạch hóa gia đình sau sinh và nuôi con bằng sữa mẹ; cung cấp can thiệp dự phòng trong phạm vi chính sách cho phép; đặt lịch tiếp theo; nhắc dấu hiệu nguy hiểm và thông tin vận chuyển cấp cứu.

## Logic hỗ trợ quyết định

### Nhóm bảng quyết định trong DAK
DAK liệt kê các logic cho: dấu hiệu nguy hiểm; HEADSS ở vị thành niên; triệu chứng thường gặp; khám thể chất; đánh giá chuyển dạ; tiêu chí chuyển tuyến; siêu âm; xét nghiệm HIV, viêm gan B/C, giang mai, nước tiểu và lao; tăng huyết áp/tiền sản giật; đái tháo đường thai kỳ; thiếu máu và bổ sung sắt–acid folic; calcium/vitamin A; tư vấn nguy cơ; tiêm chủng; tư vấn nuôi con bằng sữa mẹ, kế hoạch hóa gia đình, kế hoạch sinh; bạo lực bạn tình; tẩy giun; dự phòng sốt rét.

### Ví dụ logic tăng huyết áp/tiền sản giật trong DAK
Tài liệu minh họa logic quyết định theo cấu trúc If–Then. Ví dụ: nếu huyết áp tâm thu từ 140 đến dưới 160 mmHg và lần đo lặp lại vẫn trong khoảng này, hoặc huyết áp tâm trương từ 90 đến dưới 110 mmHg và đo lặp lại vẫn như vậy; đồng thời không có triệu chứng tiền sản giật nặng và que thử nước tiểu có protein mức ++ hoặc +++ → đầu ra là “tiền sản giật” và hành động là chuyển khẩn tới bệnh viện, đồng thời điều chỉnh kế hoạch sinh. Đây là ví dụ vận hành số trong DAK, không thay thế tiêu chuẩn chẩn đoán/điều trị của guideline lâm sàng hiện hành.

## Logic lịch chăm sóc

### Các nhóm lịch phải được hệ thống hóa
- `ANC.S.01`: lịch các lần tiếp xúc ANC theo mô hình khuyến nghị.
- `ANC.S.02`: lịch xét nghiệm và hình ảnh học.
- `ANC.S.03`: lịch tư vấn trong thai kỳ.
- `ANC.S.04`: lịch tiêm chủng được khuyến nghị trong thai kỳ.
- `ANC.S.05`: lịch dự phòng sốt rét trong các bối cảnh có chỉ định.

Hệ thống phải tính được lần tiếp xúc tiếp theo dựa trên tuổi thai và lịch được cấu hình, đồng thời hỗ trợ các lịch riêng cho xét nghiệm, tiêm chủng và can thiệp dự phòng. Các lịch cụ thể phải bám guideline và chính sách quốc gia được cấu hình cho hệ thống.

## Yêu cầu chức năng quan trọng

### Nhận diện, dữ liệu và tính liên tục
- Tìm người bệnh trước khi tạo hồ sơ mới để giảm bản ghi trùng.
- Cho phép định danh tạm trong cấp cứu.
- Có encounter riêng cho mỗi lần tiếp xúc, kèm ngày giờ.
- Tính tuổi thai từ LMP — last menstrual period, ngày đầu kỳ kinh cuối — khi dữ liệu phù hợp.
- Hiển thị lịch sử y khoa và dữ liệu từ lần trước.
- Có biểu mẫu chuẩn cho hồ sơ ANC và dữ liệu lâm sàng.
- Kiểm tra phạm vi giá trị và tính hợp lệ theo thời gian thực.

### Hỗ trợ lâm sàng
- Phát hiện quick-check bất thường và flag ca cần ưu tiên.
- Hiển thị xét nghiệm có thể chỉ định và tạo yêu cầu xét nghiệm.
- Làm nổi bật giá trị bất thường.
- Cung cấp hỗ trợ quyết định theo ngữ cảnh sau khi nhập dữ liệu.
- Gợi ý điều tra/xử trí theo rule đã cấu hình, nhưng không vượt phạm vi hành nghề của người dùng.
- Hỗ trợ referral và lưu thông tin nơi nhận.

### Lịch, nhắc và theo dõi bỏ hẹn
- Hiển thị ngày có thể đặt lịch, số lượng lịch theo ngày và ngày ưu tiên theo protocol.
- Lưu thông tin liên hệ/tracking khi phù hợp và có sự đồng ý.
- Cho phép lập danh sách phụ nữ có hẹn và phát hiện người bỏ hẹn để theo dõi.
- Hỗ trợ nội dung tự chăm sóc dễ hiểu cho người dùng cuối và bảo đảm tính riêng tư khi gửi thông tin nhạy cảm.

## Yêu cầu bảo mật và vận hành hệ thống

### Bảo mật và quyền riêng tư
- Truy cập bằng tài khoản/mật khẩu cho người được cấp quyền.
- Phân quyền theo vai trò và, khi cần, theo khu vực/cơ sở.
- Bảo vệ tính riêng tư của thông tin sức khỏe cá nhân.
- Ẩn danh dữ liệu khi xuất ra cho mục đích không cần nhận diện cá nhân.
- Mã hóa giao tiếp giữa các thành phần hệ thống.
- Tự động đăng xuất sau thời gian không hoạt động và khóa tài khoản sau số lần đăng nhập sai được cấu hình.

### Audit log
Hệ thống cần ghi log đăng nhập/đăng xuất, vi phạm xác thực, hoạt động của người dùng kèm ngày giờ, truy cập hồ sơ cá thể, truy cập báo cáo, trao đổi dữ liệu với hệ thống khác và lỗi hệ thống. Các sửa đổi hồ sơ phải có khả năng truy vết và phiên bản trước cần có thể phục hồi khi cấu hình cho phép.

### Khả năng chịu mất điện/mất mạng
Hệ thống nên hoạt động trong môi trường có mất điện hoặc mất kết nối; hỗ trợ online/offline; hiển thị số bản ghi chưa đồng bộ; có sao lưu dễ thực hiện và cảnh báo khi không có bản sao lưu hợp lệ trong khoảng thời gian được cấu hình. Đây là yêu cầu quan trọng với triển khai ANC tại khu vực hạ tầng không ổn định.

### Khả dụng và tiếp cận
Hệ thống cần phù hợp với người có kỹ năng máy tính hạn chế, có thông báo lỗi dễ hiểu, tránh mất dữ liệu khi rời biểu mẫu chưa lưu, dùng danh sách/radio/checkbox để giảm nhập tay, hỗ trợ nhiều ngôn ngữ, điều chỉnh màn hình nhỏ và cung cấp hướng dẫn ngay trong workflow để hỗ trợ guideline và thực hành lâm sàng tốt.

## Cảnh báo khi dùng DAK trong CareBridge

### Không biến DAK thành nguồn chỉ định độc lập
DAK là lớp vận hành để số hóa guideline. Khi RAG truy xuất câu hỏi về chẩn đoán, thuốc, liều, xét nghiệm hay xử trí cấp cứu, nên ưu tiên guideline lâm sàng gốc tương ứng. DAK phù hợp nhất để trả lời về workflow, cấu trúc dữ liệu, decision support, referral, scheduling, bảo mật, audit, theo dõi bỏ hẹn và thiết kế hệ thống số.

### Quy tắc an toàn
Các cảnh báo số phải có đường dẫn rõ tới hành động của con người. Hệ thống hỗ trợ quyết định không thay thế đánh giá lâm sàng. Mọi logic phải được xác thực với chính sách hiện hành, nguồn guideline được quản lý phiên bản và phạm vi hành nghề của nhân viên y tế trước khi triển khai.
