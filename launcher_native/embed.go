package launcher_native

import _ "embed"

//go:embed assets/app_payload.zip
var EmbeddedAppPayload []byte

//go:embed assets/python_embed.zip
var EmbeddedPythonZip []byte

//go:embed assets/launcher_icon.png
var EmbeddedIconPNG []byte
