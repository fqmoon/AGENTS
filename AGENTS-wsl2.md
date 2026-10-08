# 本地环境规则

## subagent 配置

subagent 应该选择便宜、快速的模型。默认使用 `gpt-6-luna + high`，除非用户明确要求。

## 环境

当前运行环境是 WSL2，已经安装了下列高级命令，建议优先使用：

- rg (ripgrep), 文本搜索工具，可代替 grep
- fdfind (fd), 文件查找工具，可代替 find
- jq, json 解析、查询、处理工具
