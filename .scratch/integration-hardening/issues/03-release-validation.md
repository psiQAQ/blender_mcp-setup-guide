Status: ready-for-agent
Category: bug
Implementation: complete

# 升级、报告与发布回执

公开安装报告成功/失败使用同一路径；升级默认锁定真实发布包，显式机制夹具支持 patch=0；发布后回执独立不可变且支持上传重试；巡检固定稳定基线 tag/commit。

验收：单元测试与本地真实旧代码升级 Passed。三平台公开安装、回执上传和远端 CI Not Run。
