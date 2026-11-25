# English_learning
This is a repository to learn english writing through the advice of gpt. The main method is copy.

## 统一排版 PDF

[下载十篇合订本（127 页，含可点击目录和书签）](output/pdf/English_Writing_Collection.pdf)

统一采用 A4、12 磅 Liberation Serif 衬线字体、16.5 磅行距及约 22 毫米左右页边距。正文可搜索、可复制，字体嵌入 PDF。标题与正文接排，各篇另起一页，不设置独立封面或奇偶页补白。

| 顺序 | 作者 | 单篇 PDF | 页数 |
| --- | --- | --- | ---: |
| 1 | George Orwell | [Politics and the English Language](output/pdf/01_Politics_and_the_English_Language.pdf) | 9 |
| 2 | John Maynard Keynes | [Economic Possibilities for Our Grandchildren](output/pdf/02_Economic_Possibilities_for_Our_Grandchildren.pdf) | 7 |
| 3 | Thomas Paine | [Agrarian Justice](output/pdf/03_Agrarian_Justice.pdf) | 14 |
| 4 | Jonathan Swift | [A Modest Proposal](output/pdf/04_A_Modest_Proposal.pdf) | 6 |
| 5 | Oscar Wilde | [The Soul of Man under Socialism](output/pdf/05_The_Soul_of_Man_under_Socialism.pdf) | 21 |
| 6 | Adam Smith | [The Wealth of Nations, Book I, Chapters 1-3](output/pdf/06_The_Wealth_of_Nations.pdf) | 11 |
| 7 | John Stuart Mill | [On Liberty, Chapter II](output/pdf/07_Of_the_Liberty_of_Thought_and_Discussion.pdf) | 24 |
| 8 | Frederick Douglass | [What to the Slave Is the Fourth of July?](output/pdf/08_What_to_the_Slave_Is_the_Fourth_of_July.pdf) | 17 |
| 9 | W. E. B. Du Bois | [Of the Dawn of Freedom](output/pdf/09_Of_the_Dawn_of_Freedom.pdf) | 12 |
| 10 | Edmund Burke | [Speech on Conciliation with America（原文件所含节选）](output/pdf/10_Speech_on_Conciliation_with_America.pdf) | 5 |

整理范围以本仓库书单为准：《国富论》原文件是全书，统一版选取第一卷前三章；伯克原文件本身是节选，统一版保留该节选范围。原始十份 PDF 全部保留在各自目录中。

已移除网页导航、订阅区、重复页眉页脚和孤立封面，恢复段落、脚注与诗歌分行，展开印刷连字并修复可核实的缺字、粘连词及转录错误。《土地正义》原 PDF 行尾被裁掉的文字已按来源恢复，并对照历史版本核查；保留各篇原有的历史拼写。具体处理记录见[整理与校对说明](reading_texts/EDITORIAL_NOTES.md)。

全部 11 份输出均通过空白页、字体覆盖、文字越界和正文逐段回读检查；合订本全部 127 页已渲染检查，目录、表格、脚注与诗歌页面另作放大检查。[构建检查记录](output/pdf/build_report.json)包含页数、目录起始页和 SHA-256。

### 重新生成

整理后的 UTF-8 文本与结构保存在 `reading_texts/01_*.json` 至 `10_*.json`。修改文本后运行：

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/build_pdfs.py --verify
```

系统需安装 Liberation Serif 的 Regular、Bold、Italic、BoldItalic 四个 TTF 字体；其他字体目录可通过 `--font-dir /path/to/fonts` 指定。检查还需 `pdfplumber`。可用 Poppler 的 `pdftoppm` 将新 PDF 渲染为图片进行版面复核。

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
