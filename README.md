# Data_Appsheet_web

Giao diện web để tải data AppSheet (view DATA TỔNG HỢP) và quản lý lịch tự động. Trang chạy trên GitHub Pages, còn việc tải dữ liệu chạy ở repo private `linhvexdd/Data_Appsheet`.

- `index.html`: web app (Tải ngay, Lịch tự động, Lịch sử)
- `schedules.json`: danh sách lịch, web sửa trực tiếp
- `scheduler.py` + `.github/workflows/lich-tu-dong.yml`: kiểm tra lịch mỗi 10 phút và gọi workflow tải data
- `columns.json`: danh sách cột của view

## Cài đặt
1. **Settings → Pages**: Source chọn *Deploy from a branch*, branch `main`, thư mục `/ (root)`.
2. Tạo Fine-grained token (GitHub → Settings → Developer settings → Personal access tokens → Fine-grained), chọn 2 repo `Data_Appsheet` và `Data_Appsheet_web`, quyền **Actions: Read and write**, **Contents: Read and write**.
3. **Settings → Secrets and variables → Actions** của repo này: thêm secret `DISPATCH_TOKEN` = token ở bước 2.
4. Mở trang web, bấm **Cài đặt**, dán cùng token đó (chỉ lưu trên trình duyệt).

Lưu ý: GitHub tự tắt lịch (cron) của repo không có hoạt động trong 60 ngày; mỗi lần lưu lịch trên web là một hoạt động.
