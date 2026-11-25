# 整理、来源与完整性核对

根据用户授权，十篇均重新查找网上可靠全文，以核对后的文本生成统一版，并直接覆盖各文章原目录中的 PDF。`output/pdf/` 同时提供十份单篇和一份 151 页合订本。旧文件仍可在 Git 历史 `7b38e2f` 中追溯。

## 逐篇来源与范围

| 顺序 | 来源 | 收录范围与核对结果 |
| --- | --- | --- |
| 1 | [The Orwell Foundation](https://www.orwellfoundation.com/the-orwell-foundation/orwell/essays-and-other-works/politics-and-the-english-language/) | 完整文章、五段示例、六条规则和三条作者注。旧版正文没有整段缺失；按网页原文恢复斜体。 |
| 2 | [The Economics Network](https://www.economicsnetwork.ac.uk/archive/keynes_persuasion/Economic_Possibilities_for_our_Grandchildren.htm) | 完整文章 I、II 两部分，包括两段诗和《Sylvie and Bruno》的完整对话。核对到结尾 dentists 一段。 |
| 3 | [Project Gutenberg 31271](https://www.gutenberg.org/ebooks/31271) | Conway 编《The Writings of Thomas Paine》第三卷第二十八篇，完整题辞、英文序言和正文。核对两张金额表，并补回潘恩关于 Horsley 的作者原注。 |
| 4 | [Project Gutenberg 1080](https://www.gutenberg.org/ebooks/1080) | 完整文章，至结尾作者声明。旧版正文没有整段缺失。 |
| 5 | [Project Gutenberg 1017](https://www.gutenberg.org/ebooks/1017) | 完整文章，至 “The new Individualism is the new Hellenism.”；沿用该版本的 æ 等历史拼写并恢复斜体。 |
| 6 | [Project Gutenberg 3300](https://www.gutenberg.org/ebooks/3300) | 第一卷完整前三章。保留 fire engines 的解释注，以单独注释呈现，不混入正文。 |
| 7 | [Project Gutenberg 34901](https://www.gutenberg.org/ebooks/34901) | 完整第二章与作者注 [6] 至 [10]。不收录其他章节或后来编者的导读。 |
| 8 | [Frederick Douglass Papers Project](https://frederickdouglasspapersproject.com/s/digitaledition/item/16068) | 完整演说与结尾四节诗。恢复打印行内断词，补回 “Rev. R. R. Raymond.” 作者原注；排除现代研究者的弹出注释。 |
| 9 | [Project Gutenberg 408](https://www.gutenberg.org/ebooks/408) | 完整第二章、洛威尔引诗及原有乐谱题图。修复旧文件的 `uch` 缺首字母问题；按来源保留 cælo、protégés 等词。 |
| 10 | [Project Gutenberg 5655](https://www.gutenberg.org/ebooks/5655) | **完整演说**，从 “I hope, Sir” 至最后提出第一项决议。旧文件只有中间一段节选，现已补齐开头、后续论证和结尾；单篇从 5 页增为 34 页。 |

Gutenberg 主站下载返回 503，因此使用相同电子书的镜像 HTML；主站书目链接、实际下载 URL、原始下载内容的 SHA-256、字符编码、范围、正文首尾及文本指纹均保存在 [source_audit.json](source_audit.json)。潘恩原 HTML 使用 ISO-8859-1，按声明解码，避免把重音字母误当 UTF-8。

## 转录修复与版本差异

完整性以所列版本中的文章或指定章节为单位核对。保留历史拼写、普通版本措辞差异和原文强调，不把网站导航、页码或现代导读混入正文。

潘恩的 Conway 转录存在少量明显错误，结合[潘恩历史协会文本](https://thomaspaine.org/major-works/agrarian-justice/)和[1797 年版转录](https://en.wikisource.org/wiki/Agrarian_Justice)校正：`hypocracy`、`chief enterions`、`principal that admits`、`5,666,6667L.`、`get cut of that state`、`fund in rance`。金额表与该版本的两张原图核对后重新排成文字表格。正文中的旧式货币记号 L. 保留。

道格拉斯数字版把 addressing、government、worship 等词拆在打印换行处，另有 `how]`、`Africal!`、`ln speaking`、`darkest comers` 等明显转录错误，已恢复为连续单词及正确读法。作者自己的星号注保留，研究版后加的编号注和人物弹出框不进入演说正文。诗歌保持分行。

在忽略大小写、标点与排版后，奥威尔、凯恩斯和斯威夫特与上一版的正文词序一致；其余多数差异是恢复断词、版本拼写、注释和强调。伯克则补入原文件没有的约两万词。新增乐谱图保存在 `reading_texts/assets/09_score2.jpg`，文章 JSON 中记录其校验值。

## 排版与验证

- 使用 XeLaTeX 排印；A4；正文 12 磅 Liberation Serif，行距 16.5 磅，左右边距约 22 毫米；字体嵌入 PDF。
- 标题与正文接排，各篇另起一页，不设置独立封面或双面打印补白；合订本首页兼作可点击目录，章节标题写入 PDF 书签。
- 保留段落、斜体、粗体、引文、作者注、诗歌分行及乐谱；清除导航、订阅区、重复页眉页脚和页码。
- 统一处理直引号、破折号、印刷连字和不可见字符，规范硬换行；正文中的排版参数集中在 `latex/preamble.tex`。

`scripts/build_pdfs.py --verify --overwrite-inputs` 会先从 JSON 重新生成 `latex/` 下的 LaTeX 源码，再编译十份单篇和合订本。检查使用 Poppler 的 `pdfinfo`、`pdffonts` 和 `pdftotext`：核对 A4 纸张、空白页、字体嵌入、文字边界和常见乱码，并把正文、诗节、标题、表格逐段回读，验证顺序及跨页内容；LaTeX 日志同时拦截溢出行和缺字。全部检查通过后才同步覆盖原目录 PDF。合订本 151 页另经 `pdftoppm` 渲染抽查，重点放大核查目录、金额表、注释、乐谱、诗歌和完整伯克演说的开头与结尾。

正文快照保存在 `01_*.json` 至 `10_*.json`；`scripts/build_pdfs.py` 生成 `latex/` 源码，`scripts/import_web_texts.py` 可从保存的来源 HTML 重新导入。图像、文本、下载来源和 LaTeX 源码均可追溯。[构建检查记录](../output/pdf/build_report.json)保存当前排印引擎、页数、目录起始页与输出文件 SHA-256。
