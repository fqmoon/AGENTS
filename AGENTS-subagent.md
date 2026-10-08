# Subagent 配置

## 使用场景

对于相对独立的任务，以及代码 Review 等需要独立判断的工作，应优先考虑使用 subagent，以减少 main agent 的上下文污染或上下文过长的问题。

## 默认模型建议

subagent 应该选择便宜、快速的模型。默认使用 `gpt-6-luna + high`，除非用户明确要求。
