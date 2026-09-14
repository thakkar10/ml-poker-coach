extends Node
## The server owns poker rules, legal actions, cards and settlement.

var base_url := "http://127.0.0.1:8000"

func _ready() -> void:
	if OS.has_feature("web"):
		base_url = str(JavaScriptBridge.eval("window.location.origin"))
	elif not OS.get_environment("POKER_API_URL").is_empty():
		base_url = OS.get_environment("POKER_API_URL").trim_suffix("/")

func send(path: String, body: Variant = null) -> Dictionary:
	var request := HTTPRequest.new()
	request.timeout = 45.0
	add_child(request)
	var method := HTTPClient.METHOD_GET if body == null else HTTPClient.METHOD_POST
	var data := "" if body == null else JSON.stringify(body)
	var error := request.request(base_url + path, ["Content-Type: application/json"], method, data)
	if error != OK:
		request.queue_free()
		return {"error": "Could not connect to the table. Reconnect to try again."}
	var response: Array = await request.request_completed
	request.queue_free()
	if response[0] != HTTPRequest.RESULT_SUCCESS:
		return {"error": "Connection interrupted. Reconnect to recover your hand."}
	var parsed: Variant = JSON.parse_string(response[3].get_string_from_utf8())
	if not parsed is Dictionary:
		return {"error": "The table returned an unreadable response."}
	if response[1] < 200 or response[1] >= 300:
		return {"error": str(parsed.get("detail", "The table could not accept that action."))}
	return parsed
