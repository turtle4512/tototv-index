# tototv-index

TotoTV 电视 App 的片名拼音首字母名单：5 个公开片源的全部片名 → `index.txt.gz`（每行 `首字母\t片名`，按首字母排序）。

- `python crawl.py full`：全量翻页（首次）
- `python crawl.py inc`：增量，只拉最近 48 小时更新的；GitHub Actions 每天跑一次并提交
