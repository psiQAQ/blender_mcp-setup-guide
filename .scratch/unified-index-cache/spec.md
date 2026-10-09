# 统一扩展索引与当前成果保留

Status: ready-for-agent
Category: enhancement

根索引使用 Blender v1 格式，各 Blender 发布线稳定版优先，否则采用预览版。独立通道保留安装包信息与索引字节；根 publication.json 兼容 5.1。双语网站推荐根索引，详细说明提供独立链接。

本地仅保留 build/latest 中一套当前成果、锁定输入及最新诊断；长期参考进入 docs/references，可复用脚本进入 scripts。清理前逐项核验保留哈希，拒绝仓库外目标；占用或拒绝访问的对象留在原处。

验收包括单元测试、5.1.1/5.2.2 实际索引同步、最终 Windows 包的官方校验及 MCP/CLI/生命周期/GUI/真实升级、双语手机与索引复制、清理前后体积和再次运行不累积。main 分批提交后统一 push，跟踪自动 CI 和 Pages；本次不发布安装包。
