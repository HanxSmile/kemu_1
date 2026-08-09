# 科目一学习册

把驾校一点通精选 500 题与完整题库增补内容整理成可搜索、可练习的口诀学习网页。

## 在线学习

[打开科目一学习册](https://hanxsmile.github.io/kemu_1/)

## 学习方式

- 在“按章节”和“按口诀”之间切换。
- 口诀分为数字记忆、图形识别、关键词直选、行为原则、法规归纳。
- 点开一条口诀后，可在右侧选择全部关联题目。
- 支持背题、练习、易混标记、记住状态和本地进度保存。
- 当前包含 391 条口诀、535 道代表题和 189 张题图。

## 本地运行

```bash
cd web
npm ci
npm run dev
```

生成数据与检查生产构建：

```bash
python3 scripts/build_web_data.py
npm --prefix web run build
npm --prefix web run test:sites
```

网页在推送到 `main` 后由 GitHub Actions 自动发布到 GitHub Pages。
