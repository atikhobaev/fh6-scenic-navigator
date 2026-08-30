package launcher_native

var uiText = map[string]map[string]string{
	"ru-RU": {
		"stage_runtime_short": "Runtime", "stage_graph_short": "Дороги", "stage_localization_short": "Язык", "stage_server_short": "Сервер", "errors": "ошибок",
		"stage_runtime": "Подготовка встроенного runtime", "stage_graph": "Загрузка дорожного графа", "stage_localization": "Загрузка локализации FH6", "stage_server": "Запуск локального сервера", "fallback_names": "Английские названия (fallback)", "show_launcher": "Показать Launcher", "exit": "Выйти",
		"ready": "Готов к запуску", "ready_sub": "Navigator проверит данные и запустится автоматически", "start": "Запустить Navigator", "starting": "Запуск Navigator", "running": "Navigator работает", "waiting": "Сервер готов · ожидаю телеметрию FH6", "connected": "Forza подключена · телеметрия активна", "lost": "Связь с Forza потеряна · ожидаю телеметрию", "open_drive": "Открыть DRIVE", "open_plan": "Открыть PLAN", "stop": "Остановить", "fh6": "FORZA HORIZON 6", "localization": "ЛОКАЛИЗАЦИЯ", "navigation": "NAVIGATION", "network": "СЕТЬ", "game_auto": "Автопоиск при запуске", "official_names": "Официальные названия POI", "graph": "Directed WVAN готов", "pc": "PC", "phone": "PHONE", "log": "Журнал запуска", "no_errors": "без ошибок", "settings": "Настройки", "auto_drive": "Открывать DRIVE после запуска", "minimize": "Сворачивать после открытия", "tray": "Оставлять Navigator в трее", "language": "Язык интерфейса", "advanced": "Дополнительно", "ports": "HTTP 8080 · UDP 1234", "copy_log": "Копировать лог", "open_logs": "Открыть папку логов", "close_settings": "Готово", "download": "Подготовка Python runtime", "error": "Не удалось запустить Navigator", "retry": "Попробовать снова", "places": "точек", "waiting_game": "Ожидание", "telemetry": "Телеметрия", "hide_log": "Скрыть журнал", "show_log": "Показать журнал"},
	"en-US": {
		"stage_runtime_short": "Runtime", "stage_graph_short": "Road graph", "stage_localization_short": "Language", "stage_server_short": "Server", "errors": "errors",
		"stage_runtime": "Preparing portable runtime", "stage_graph": "Loading road graph", "stage_localization": "Loading FH6 localization", "stage_server": "Starting local server", "fallback_names": "English names (fallback)", "show_launcher": "Show Launcher", "exit": "Exit",
		"ready": "Ready to start", "ready_sub": "Navigator will validate data and start automatically", "start": "Start Navigator", "starting": "Starting Navigator", "running": "Navigator is running", "waiting": "Server ready · waiting for FH6 telemetry", "connected": "Forza connected · telemetry active", "lost": "Forza connection lost · waiting for telemetry", "open_drive": "Open DRIVE", "open_plan": "Open PLAN", "stop": "Stop", "fh6": "FORZA HORIZON 6", "localization": "LOCALIZATION", "navigation": "NAVIGATION", "network": "NETWORK", "game_auto": "Auto-detected at startup", "official_names": "Official POI names", "graph": "Directed WVAN ready", "pc": "PC", "phone": "PHONE", "log": "Launch log", "no_errors": "no errors", "settings": "Settings", "auto_drive": "Open DRIVE after launch", "minimize": "Minimize after opening", "tray": "Keep Navigator in tray", "language": "Interface language", "advanced": "Advanced", "ports": "HTTP 8080 · UDP 1234", "copy_log": "Copy log", "open_logs": "Open logs folder", "close_settings": "Done", "download": "Preparing Python runtime", "error": "Navigator could not start", "retry": "Try again", "places": "places", "waiting_game": "Waiting", "telemetry": "Telemetry", "hide_log": "Hide log", "show_log": "Show log"},
	"zh-CN": {
		"stage_runtime_short": "运行环境", "stage_graph_short": "道路图", "stage_localization_short": "语言", "stage_server_short": "服务器", "errors": "错误",
		"stage_runtime": "准备便携运行环境", "stage_graph": "加载道路图", "stage_localization": "加载 FH6 本地化", "stage_server": "启动本地服务器", "fallback_names": "英文名称（备用）", "show_launcher": "显示启动器", "exit": "退出",
		"ready": "准备启动", "ready_sub": "Navigator 将自动检查数据并启动", "start": "启动 Navigator", "starting": "正在启动 Navigator", "running": "Navigator 正在运行", "waiting": "服务器已就绪 · 等待 FH6 遥测", "connected": "Forza 已连接 · 遥测正常", "lost": "与 Forza 的连接已断开 · 等待遥测", "open_drive": "打开 DRIVE", "open_plan": "打开 PLAN", "stop": "停止", "fh6": "FORZA HORIZON 6", "localization": "本地化", "navigation": "导航数据", "network": "网络", "game_auto": "启动时自动检测", "official_names": "官方 POI 名称", "graph": "Directed WVAN 已就绪", "pc": "本机", "phone": "手机", "log": "启动日志", "no_errors": "无错误", "settings": "设置", "auto_drive": "启动后打开 DRIVE", "minimize": "打开后最小化", "tray": "在托盘中保持运行", "language": "界面语言", "advanced": "高级", "ports": "HTTP 8080 · UDP 1234", "copy_log": "复制日志", "open_logs": "打开日志文件夹", "close_settings": "完成", "download": "准备 Python runtime", "error": "Navigator 启动失败", "retry": "重试", "places": "地点", "waiting_game": "等待", "telemetry": "遥测", "hide_log": "隐藏日志", "show_log": "显示日志"},
	"es-419": {
		"stage_runtime_short": "Runtime", "stage_graph_short": "Red vial", "stage_localization_short": "Idioma", "stage_server_short": "Servidor", "errors": "errores",
		"stage_runtime": "Preparando runtime portable", "stage_graph": "Cargando red vial", "stage_localization": "Cargando localización de FH6", "stage_server": "Iniciando servidor local", "fallback_names": "Nombres en inglés (respaldo)", "show_launcher": "Mostrar Launcher", "exit": "Salir",
		"ready": "Listo para iniciar", "ready_sub": "Navigator verificará los datos y se iniciará automáticamente", "start": "Iniciar Navigator", "starting": "Iniciando Navigator", "running": "Navigator está activo", "waiting": "Servidor listo · esperando telemetría de FH6", "connected": "Forza conectado · telemetría activa", "lost": "Se perdió la conexión con Forza · esperando telemetría", "open_drive": "Abrir DRIVE", "open_plan": "Abrir PLAN", "stop": "Detener", "fh6": "FORZA HORIZON 6", "localization": "LOCALIZACIÓN", "navigation": "NAVEGACIÓN", "network": "RED", "game_auto": "Detección automática al iniciar", "official_names": "Nombres oficiales de POI", "graph": "Directed WVAN listo", "pc": "PC", "phone": "TELÉFONO", "log": "Registro de inicio", "no_errors": "sin errores", "settings": "Configuración", "auto_drive": "Abrir DRIVE al iniciar", "minimize": "Minimizar después de abrir", "tray": "Mantener Navigator en la bandeja", "language": "Idioma de la interfaz", "advanced": "Avanzado", "ports": "HTTP 8080 · UDP 1234", "copy_log": "Copiar registro", "open_logs": "Abrir carpeta de registros", "close_settings": "Listo", "download": "Preparando Python runtime", "error": "No se pudo iniciar Navigator", "retry": "Intentar de nuevo", "places": "lugares", "waiting_game": "Esperando", "telemetry": "Telemetría", "hide_log": "Ocultar registro", "show_log": "Mostrar registro"},
}

func T(locale, key string) string {
	if d, ok := uiText[locale]; ok {
		if v := d[key]; v != "" {
			return v
		}
	}
	return uiText["en-US"][key]
}
func NextLocale(locale string) string {
	switch locale {
	case "ru-RU":
		return "en-US"
	case "en-US":
		return "zh-CN"
	case "zh-CN":
		return "es-419"
	default:
		return "ru-RU"
	}
}
func LocaleShort(locale string) string {
	switch locale {
	case "ru-RU":
		return "RU"
	case "zh-CN":
		return "中文"
	case "es-419":
		return "ES"
	default:
		return "EN"
	}
}
