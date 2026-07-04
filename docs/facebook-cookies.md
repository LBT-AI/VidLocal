# Facebook cookies cho yt-dlp

`FACEBOOK_COOKIES_FILE` trỏ tới file cookies Facebook dạng Netscape txt:

```env
FACEBOOK_COOKIES_FILE=/root/vidlocal/cookies/facebook.txt
```

Trong Docker, file host nên nằm tại:

```text
/root/vidlocal/cookies/facebook.txt
```

File sẽ được mount read-only vào API/worker container cùng path.

## Tạo cookies Netscape txt

1. Đăng nhập Facebook trên trình duyệt.
2. Cài extension xuất cookies dạng `cookies.txt`/Netscape, ví dụ "Get cookies.txt LOCALLY".
3. Mở `facebook.com`, export cookies cho domain Facebook.
4. Lưu file thành `cookies/facebook.txt`.
5. Không commit file cookies. Đây là dữ liệu nhạy cảm.

## Test thủ công

Kiểm tra format tải được:

```bash
yt-dlp --cookies "$FACEBOOK_COOKIES_FILE" -F "<url>"
```

Thử tải bằng format production đang dùng:

```bash
yt-dlp --cookies "$FACEBOOK_COOKIES_FILE" -f "bv*+ba/best" "<url>"
```

Nếu không dùng cookies:

```bash
yt-dlp -F "<url>"
yt-dlp -f "bv*+ba/best" "<url>"
```
