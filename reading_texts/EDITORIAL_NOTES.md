# 整理与校对说明

本次生成十份单篇 PDF 和一份 127 页合订本，保留仓库中的全部原始 PDF。学习顺序沿用原 README。

## 收录范围

- 前五篇收录原文件中的文章正文；潘恩另保留法文版题辞和英文版序言。
- 斯密依原书单收录《国富论》第一卷第一至第三章，取自原 PDF 第 9 至 19 页。552 页原书保留不动。
- 密尔收录《论自由》第二章及原文件的注释 [6] 至 [10]，保留原注号。
- 道格拉斯收录原阅读版演说正文与结尾诗歌。
- 杜波依斯收录《黑人的灵魂》第二章与开篇洛威尔引诗。
- 伯克收录原文件已经选出的部分，题下注明 Excerpt，不将其标作完整演说。来源为《The Founders' Constitution》第一卷第一章第二份文献。

## 排版与字符

- A4；正文 12 磅 Liberation Serif，行距 16.5 磅；左右边距 62 磅，约 22 毫米。
- 统一作者、标题、层级、页码与来源信息；单篇标题直接接正文，合订本仅有一页兼作目录的首页。
- 章节按内容连续排版，各篇另起一页；不插入为双面打印补齐奇偶页的空白页。
- 删除网页导航、订阅框、网站推荐、社交图标、网页式封面与原有重复页眉页脚。保留来源、注释与原文件附带的版权声明。
- 展开 fi/fl/ff 等 PDF 印刷连字，清除软连字符和不可见控制字符；保留真实复合词的连字符，去除硬换行造成的词内空格。长短破折号统一为可移植的 ASCII 连字符形式。
- 保留可辨识的原段落、引文、注释编号和诗歌分行。没有把历史拼写改成现代拼写，也没有翻译或改写论述。

## 可核实的转录修复

《Agrarian Justice》原 PDF 存在行尾裁字，不能仅靠重新提取 PDF 修复。以原文件相同的 [SSA 转录](https://www.ssa.gov/history/paine4.html)恢复被裁掉的字符，再对照[托马斯·潘恩历史协会转录](https://thomaspaine.org/major-works/agrarian-justice/)和 [1797 年版转录](https://en.wikisource.org/wiki/Agrarian_Justice)检查明显缺字、粘连词与转录错误。

例如恢复 `this`、`have` 等被裁掉的行尾，拆开 `inpassing` / `kindof` / `numerairefor`，修复 `parable connection` 为 `inseparable connection`、`cultivated state` 为 `uncultivated state`、`twenty-ope` 为 `twenty-one`。继承分配段落中的 `£413,333,333` 按历史文本及原表格修正为 `£13,333,333`，补回执行办法第五项的 `V.`。两张金额表重排为可读表格；修复条目保存在 [paine_corrections.json](paine_corrections.json)。

另将密尔原文件开篇的明显赘字 `than when in or opposition` 修为 `than when in opposition`。正文与参考版本之间的普通措辞或拼写差异不作全面替换。

各文章 JSON 保存原 PDF 的相对路径和 SHA-256，便于追溯。整理结果以这些 UTF-8 文本快照作为重新排版的输入。

## 检查

`scripts/build_pdfs.py --verify` 对每份输出检查：

1. 页面均为 A4，且每页有实际正文或目录内容。
2. 不含替代字符、私用区图标、黑方块或不支持的字体字符。
3. 使用的 TrueType 正文字体已嵌入 PDF。
4. 可见文字没有超出页边界。
5. 去除新页眉页脚后，每个完整段落、标题、诗节和表格单元格都能按顺序从最终 PDF 提取回来，包括跨页长段落。

另用 Poppler 渲染合订本全部 127 页检查排版，放大复核目录、正文开篇、金额表、注释和诗歌。单篇与合订本各篇的页数、起始页和正文对应关系均已核对。结果见 [build_report.json](../output/pdf/build_report.json)。
