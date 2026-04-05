# UI 用户界面模块

主窗口和 Dock 布局管理。

## 文件清单

| 文件 | 类 | 说明 |
|------|-----|------|
| `main_window.py` | `MainWindow` | QMainWindow 主窗口，整合菜单/工具栏/状态栏/Dock |
| `dock_manager.py` | `DockManager` | 管理 QDockWidget 面板的停靠/布局/保存/恢复 |

## MainWindow 功能

- 菜单栏：文件（打开DB/导出）、视图（面板显隐/布局）、工具（主题切换）、帮助
- 工具栏：常用操作快捷按钮
- 状态栏：连接 `SignalBus.sigStatusMessage` 显示操作反馈
- Dock 管理：三层面板以 QDockWidget 形式停靠
- 布局保存：通过 QSettings 保存/恢复窗口几何和 Dock 状态
- 快捷键：Ctrl+1/2/3 切换图层焦点

## DockManager 功能

- 注册/注销 QDockWidget（自动设置停靠区域和标题）
- 预设布局方案（水平三分/垂直堆叠/Tab合并）
- 布局序列化/反序列化（QByteArray → QSettings）
- 面板可见性批量切换
