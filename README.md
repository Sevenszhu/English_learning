# English_learning
This is a repository for learning English writing through GPT advice. The main method is copy.

## 统一排版 PDF

[下载十篇合订本（151 页，含可点击目录和书签）](output/pdf/English_Writing_Collection.pdf)

统一使用 XeLaTeX 排印，采用 A4、12 磅 Liberation Serif 衬线字体、16.5 磅行距及约 22 毫米左右页边距。正文可搜索、可复制，字体嵌入 PDF。标题与正文接排，各篇另起一页，不设置独立封面或奇偶页补白；十篇单篇与合订本共用同一套 LaTeX 模板。

| 顺序 | 作者 | 单篇 PDF | 页数 |
| --- | --- | --- | ---: |
| 1 | George Orwell | [Politics and the English Language](output/pdf/01_Politics_and_the_English_Language.pdf) | 9 |
| 2 | John Maynard Keynes | [Economic Possibilities for Our Grandchildren](output/pdf/02_Economic_Possibilities_for_Our_Grandchildren.pdf) | 7 |
| 3 | Thomas Paine | [Agrarian Justice](output/pdf/03_Agrarian_Justice.pdf) | 12 |
| 4 | Jonathan Swift | [A Modest Proposal](output/pdf/04_A_Modest_Proposal.pdf) | 6 |
| 5 | Oscar Wilde | [The Soul of Man under Socialism](output/pdf/05_The_Soul_of_Man_under_Socialism.pdf) | 20 |
| 6 | Adam Smith | [The Wealth of Nations, Book I, Chapters 1-3](output/pdf/06_The_Wealth_of_Nations.pdf) | 10 |
| 7 | John Stuart Mill | [On Liberty, Chapter II](output/pdf/07_Of_the_Liberty_of_Thought_and_Discussion.pdf) | 23 |
| 8 | Frederick Douglass | [What to the Slave Is the Fourth of July?](output/pdf/08_What_to_the_Slave_Is_the_Fourth_of_July.pdf) | 17 |
| 9 | W. E. B. Du Bois | [Of the Dawn of Freedom](output/pdf/09_Of_the_Dawn_of_Freedom.pdf) | 12 |
| 10 | Edmund Burke | [Speech on Conciliation with America（完整演说）](output/pdf/10_Speech_on_Conciliation_with_America.pdf) | 34 |

十篇均已重新在网上查找可靠版本并核对完整性。伯克原文件只有节选，现已换成完整演说；《国富论》收录第一卷完整前三章，《论自由》收录完整第二章及作者脚注，范围沿用书单。各文章原目录中的十份 PDF 也已直接覆盖为核对后的统一版，旧文件可通过 Git 历史查看。

来源以 Orwell Foundation、The Economics Network、Frederick Douglass Papers Project 和 Project Gutenberg 的全文版本为主。补回了作者原注和杜波依斯章节的乐谱题图，恢复网页转录中可核实的断词、缺字及 OCR 错误，保留原文的斜体强调和历史拼写。逐篇来源、版本范围、下载校验值及正文首尾见[来源核对记录](reading_texts/source_audit.json)，具体编辑原则见[整理与校对说明](reading_texts/EDITORIAL_NOTES.md)。

全部 11 份输出均由 `scripts/build_pdfs.py` 逐页检查：A4 纸张、无空白页、字体全部嵌入、文字不越界、无乱码，并将正文逐段回读核对顺序与完整性；LaTeX 日志同时拦截溢出行和缺字。合订本 151 页另经渲染抽查，目录、金额表、作者注、乐谱、诗歌以及伯克演说的开头与结尾均作放大检查。[构建检查记录](output/pdf/build_report.json)包含排印引擎、页数、目录起始页、字体和 SHA-256。

### 重新生成

整理后的 UTF-8 文本与结构保存在 `reading_texts/01_*.json` 至 `10_*.json`，是文本的唯一来源。修改文本后运行：

```bash
python3 scripts/build_pdfs.py --verify --overwrite-inputs
```

脚本会重新生成 `latex/` 下的 XeLaTeX 源码（`preamble.tex`、十篇正文、十份单篇入口及合订本入口），编译十份单篇和合订本，并完成全部检查。系统需安装 TeX Live（含 XeLaTeX、fontspec、hyperref 等常用宏包）、Liberation Serif 字体，以及 Poppler 的 `pdfinfo`、`pdffonts`、`pdftotext`。`--overwrite-inputs` 会同步覆盖各文章原目录中的 PDF；省略该参数则仅更新 `output/pdf/`。可用 `pdftoppm` 将 PDF 渲染为图片进行版面复核。

## 十篇最终书单
- George Orwell — Politics and the English Language
训练现代英文的清楚、简洁、具体。建议第一篇。
- John Maynard Keynes — Economic Possibilities for Our Grandchildren
训练长短句节奏，以及从经济分析过渡到文明思考。
- Thomas Paine — Agrarian Justice
训练如何把抽象原则写成普通人能够理解的公共论证。
- Jonathan Swift — A Modest Proposal
训练反讽、语气控制，以及字面意义与真实意图的分离。
- Oscar Wilde — The Soul of Man under Socialism
训练警句、悖论、排比、反转和文采。
- Adam Smith — The Wealth of Nations, Book I, Chapters 1–3
即《国富论》第一卷前三章：分工、交换与市场范围。训练从具体事例推导一般原理。
- John Stuart Mill — On Liberty, Chapter II: “Of the Liberty of Thought and Discussion”
训练定义、限定、让步、反驳和严密的长篇论证。
- Frederick Douglass — What to the Slave Is the Fourth of July?
训练演说节奏、情绪蓄积、反问和道德论证。
- W. E. B. Du Bois — “Of the Dawn of Freedom”
《The Souls of Black Folk》第二章。训练历史叙述、制度分析与抒情的结合。
- Edmund Burke — Speech on Conciliation with America
训练周期长句、宏大结构、政治判断和古典雄辩。难度最高，最后学习。

# 建议顺序

Orwell → Keynes → Paine → Swift → Wilde → Smith → Mill → Douglass → Du Bois → Burke

> 前五篇先建立现代语感与个人文气；中间三篇强化论证；最后两篇学习历史感和宏大结构。
