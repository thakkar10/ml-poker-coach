extends Control

const Api = preload("res://scripts/poker_api.gd")
const Card = preload("res://scripts/poker_card.gd")
const FONT = preload("res://assets/fonts/VT323-Regular.ttf")
const GOLD := Color("eac568")
const TEXT := Color("eee9d7")
const MUTED := Color("a7b8b6")
const SEATS := [Vector2(640,557),Vector2(245,452),Vector2(245,201),Vector2(640,186),Vector2(1035,201),Vector2(1035,452)]
const BETS := [Vector2(640,443),Vector2(391,432),Vector2(393,250),Vector2(780,246),Vector2(887,250),Vector2(889,432)]

var api: Node
var state: Dictionary = {}
var busy := true
var board_cards: Array = []
var hole_cards: Array = []
var seat_names: Array[Label] = []
var seat_stacks: Array[Label] = []
var seat_status: Array[Label] = []
var seat_totals: Array[Label] = []
var seat_badges: Array[Label] = []
var bet_labels: Array[Label] = []
var last_actions: Dictionary = {}
var status: Label
var street: Label
var pot: Label
var turn: Label
var fold: Button
var call_button: Button
var raise_button: Button
var next_button: Button
var review_button: Button
var reconnect: Button
var raise_slider: HSlider
var raise_caption: Label
var presets: Array[Button] = []
var review_layer: Control
var review_text: RichTextLabel
var review_data: Dictionary = {}
var speed := 1.0
var muted := false
var sound: AudioStreamPlayer
var chip_position := Vector2.ZERO
var chip_visible := false
var active_progress := 0.0
var hand_number := 0
var test_mode := false
var observed_streets: Array[String] = []

func _ready() -> void:
	api = Api.new()
	add_child(api)
	var theme_resource := Theme.new()
	theme_resource.default_font = FONT
	theme_resource.default_font_size = 24
	theme = theme_resource
	_build_ui()
	_build_cards()
	_build_sound()
	test_mode = "--smoke" in OS.get_cmdline_user_args() or "--smoke-fold" in OS.get_cmdline_user_args()
	if test_mode:
		speed = 0.01
	await _new_hand()
	if test_mode:
		await _smoke()

func _process(_delta: float) -> void:
	if busy or chip_visible:
		queue_redraw()

func _label(value: String, rect: Rect2, font_size := 24, color := TEXT, centered := false, parent: Node = self) -> Label:
	var label := Label.new()
	label.text = value
	label.position = rect.position
	label.size = rect.size
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER if centered else HORIZONTAL_ALIGNMENT_LEFT
	label.clip_text = true
	label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(label)
	return label

func _box(color: Color, border: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = border
	style.set_border_width_all(2)
	style.content_margin_left = 12
	style.content_margin_right = 12
	return style

func _button(value: String, rect: Rect2, callback: Callable, primary := false, parent: Node = self) -> Button:
	var button := Button.new()
	button.text = value
	button.position = rect.position
	button.size = rect.size
	button.add_theme_stylebox_override("normal", _box(GOLD if primary else Color("203336"), Color("eaca81") if primary else Color("5c7370")))
	button.add_theme_stylebox_override("hover", _box(Color("f3d98b") if primary else Color("35534d"), GOLD))
	button.add_theme_stylebox_override("pressed", _box(Color("b99545") if primary else Color("102624"), GOLD))
	button.add_theme_stylebox_override("focus", _box(Color(0,0,0,0), TEXT))
	button.add_theme_stylebox_override("disabled", _box(Color("182526"), Color("344343")))
	button.add_theme_color_override("font_color", Color("162526") if primary else TEXT)
	button.add_theme_color_override("font_hover_color", Color("162526") if primary else TEXT)
	button.add_theme_color_override("font_pressed_color", TEXT)
	button.add_theme_color_override("font_disabled_color", Color("6f8280"))
	button.pressed.connect(callback)
	parent.add_child(button)
	return button

func _build_ui() -> void:
	_label("ML POKER COACH", Rect2(32,12,370,36), 38, GOLD)
	_label("THE PRACTICE ROOM", Rect2(33,45,350,24), 20, MUTED)
	_label("NO LIMIT HOLD'EM   /   $10-$20   /   PLAY MONEY", Rect2(385,20,460,36), 22, MUTED, true)
	_button("SOUND ON", Rect2(858,20,130,36), _toggle_sound)
	_button("PACE 1x", Rect2(1000,20,116,36), _toggle_speed)
	_button("[  ]", Rect2(1128,20,60,36), _fullscreen).tooltip_text = "Toggle fullscreen"
	_button("?", Rect2(1200,20,48,36), _show_help).tooltip_text = "Poker basics"
	for i in range(6):
		var p: Vector2 = SEATS[i] - Vector2(94,0)
		seat_names.append(_label("YOU" if i == 0 else ["","FOX","RIVER","NOVA","BLAZE","MIRA"][i], Rect2(p.x+53,p.y+4,126,25), 25))
		seat_stacks.append(_label("$1,000", Rect2(p.x+53,p.y+28,126,25), 24))
		seat_status.append(_label("", Rect2(p.x,p.y+76,188,22), 20, MUTED, true))
		seat_totals.append(_label("", Rect2(p.x+53,p.y+53,126,20), 18, MUTED))
		seat_badges.append(_label("", Rect2(p.x+24,p.y+48,26,22), 20, GOLD, true))
		bet_labels.append(_label("", Rect2(BETS[i].x-45,BETS[i].y+10,90,22), 20, TEXT, true))
	seat_status[3].position = Vector2(738,198)
	seat_status[3].size = Vector2(140,26)
	pot = _label("POT  $0", Rect2(490,278,300,32), 32, GOLD, true)
	street = _label("PREFLOP", Rect2(500,398,280,26), 23, MUTED, true)
	turn = _label("", Rect2(542,633,196,26), 24, GOLD, true)
	status = _label("Opening the table...", Rect2(32,669,550,30), 24)
	raise_caption = _label("RAISE TO", Rect2(594,669,530,30), 22, MUTED)
	raise_slider = HSlider.new()
	raise_slider.position = Vector2(598,706)
	raise_slider.size = Vector2(334,30)
	raise_slider.step = 1
	raise_slider.value_changed.connect(func(_value): _update_raise_text())
	add_child(raise_slider)
	for i in range(5):
		var preset := _button(["1/3","1/2","3/4","POT","ALL IN"][i], Rect2(594+i*94,746,86,34), _preset.bind(i))
		preset.add_theme_font_size_override("font_size",20)
		presets.append(preset)
	fold = _button("FOLD",Rect2(32,712,142,60),_act.bind("fold"))
	fold.add_theme_stylebox_override("normal",_box(Color("482d37"),Color("85616a")))
	call_button = _button("CHECK",Rect2(184,712,190,60),_call,true)
	raise_button = _button("RAISE",Rect2(952,701,296,38),_raise)
	review_button = _button("HAND REVIEW",Rect2(390,712,176,60),_show_review)
	review_button.visible = false
	next_button = _button("DEAL AGAIN",Rect2(1064,746,184,34),_new_hand)
	next_button.disabled = true
	reconnect = _button("RECONNECT",Rect2(390,712,176,60),_recover)
	reconnect.visible = false
	_build_review()

func _build_cards() -> void:
	for i in range(5):
		var card := Card.new()
		card.position = Vector2(512+i*64,351)
		add_child(card)
		board_cards.append(card)
	for i in range(6):
		var pair: Array = []
		for j in range(2):
			var card := Card.new()
			card.visible = false
			add_child(card)
			pair.append(card)
		hole_cards.append(pair)
	# The modal must stay above card sprites and moving chips.
	move_child(review_layer, get_child_count()-1)

func _card_target(seat: int, index: int) -> Vector2:
	return SEATS[seat] + Vector2(-30+index*60,-46)

func _draw() -> void:
	draw_rect(Rect2(0,0,1280,800),Color("101d23"))
	draw_rect(Rect2(0,0,1280,80),Color("0c151b"))
	draw_line(Vector2(32,79),Vector2(1248,79),Color("67705a"),2)
	for x in range(0,1280,32):
		for y in range(96,650,32):
			draw_rect(Rect2(x,y,2,2),Color("273337"))
	var outline := PackedVector2Array([Vector2(280,159),Vector2(1000,159),Vector2(1136,239),Vector2(1170,310),Vector2(1170,412),Vector2(1110,505),Vector2(966,592),Vector2(314,592),Vector2(170,505),Vector2(110,412),Vector2(110,310),Vector2(144,239)])
	draw_colored_polygon(outline,Color("080f13"))
	var rail := PackedVector2Array()
	var felt := PackedVector2Array()
	for point in outline:
		rail.append(Vector2(640,370)+(point-Vector2(640,370))*Vector2(0.97,0.94))
		felt.append(Vector2(640,370)+(point-Vector2(640,370))*Vector2(0.93,0.83))
	draw_colored_polygon(rail,Color("a39359"))
	draw_colored_polygon(felt,Color("1d624b"))
	for x in range(195,1100,8):
		for y in range(218,531,8):
			if Geometry2D.is_point_in_polygon(Vector2(x,y),felt):
				draw_rect(Rect2(x,y,1,1),Color("287052"))
	draw_rect(Rect2(466,310,348,84),Color("1b5845"))
	for i in range(6):
		var active: bool = state.get("current_player_id", "") == "p%d" % i
		var folded: bool = not state.is_empty() and state.players[i].folded
		var p: Vector2 = SEATS[i]-Vector2(94,0)
		var alpha := 0.60 if folded else 1.0
		draw_rect(Rect2(p+Vector2(4,4),Vector2(188,76)),Color(0,0,0,0.3))
		draw_rect(Rect2(p,Vector2(188,76)),Color("15272c"))
		draw_rect(Rect2(p,Vector2(188,76)),GOLD if active else Color("506465"),false,2)
		_portrait(p+Vector2(8,10),i,alpha)
		if active:
			draw_rect(Rect2(p+Vector2(0,73),Vector2(188*(1.0-active_progress),3)),GOLD)
		if not state.is_empty() and int(state.players[i].current_bet)>0 and state.street != "complete":
			_chip(BETS[i])
	if chip_visible:
		_chip(chip_position)
	draw_rect(Rect2(0,660,1280,140),Color("0c151b"))
	draw_line(Vector2(32,660),Vector2(1248,660),Color("67705a"),2)

func _portrait(pos: Vector2, index: int, alpha: float) -> void:
	var hair: Color = [Color("d9c17c"),Color("acbac5"),Color("663c47"),Color("a195bd"),Color("db8663"),Color("263747")][index]
	var skin: Color = [Color("dca884"),Color("bc886c"),Color("875b4b"),Color("ddbc9c"),Color("bc8c64"),Color("b88278")][index]
	var pixels := ["..hhhhhh..",".hhhhhhhh.",".hssssssh.",".hseksesh.","..ssssss..","..ssmmss..","...ssss...","..jjjjjj..",".jjjjjjjj.","jjjjjjjjjj"]
	for y in range(pixels.size()):
		for x in range(10):
			var key: String = pixels[y][x]
			if key == ".": continue
			var color: Color = {"h":hair,"s":skin,"e":TEXT,"k":Color("17202c"),"m":Color("663f49"),"j":hair.darkened(0.4)}[key]
			color.a = alpha
			draw_rect(Rect2(pos+Vector2(x*4,y*4),Vector2(4,4)),color)

func _chip(pos: Vector2) -> void:
	for i in range(3):
		var p := pos+Vector2(i*7,-i*3)
		draw_rect(Rect2(p-Vector2(10,5),Vector2(20,10)),Color("943d52") if i%2 == 0 else Color("486a93"))
		draw_rect(Rect2(p-Vector2(10,5),Vector2(20,2)),TEXT)
		draw_rect(Rect2(p-Vector2(2,5),Vector2(4,10)),GOLD)

func _new_hand() -> void:
	if busy and not state.is_empty(): return
	busy = true
	review_layer.visible = false
	review_data = {}
	last_actions.clear()
	state = {}
	for card in board_cards:
		card.vacant = true
		card.face_up = false
		card.code = ""
		card.queue_redraw()
	for pair in hole_cards:
		for card in pair:
			card.visible = false
			card.face_up = false
			card.modulate = Color.WHITE
			card.rotation = 0
			card.highlighted = false
	status.text = "Shuffling the deck..."
	_lock_actions()
	var body := {"player_names":["YOU","STONE FOX","RIVER JAY","NOVA","BLAZE","MIRA"]}
	if test_mode: body["seed"] = 103
	var response: Dictionary = await api.send("/api/game/new",body)
	if _failed(response): return
	hand_number += 1
	var logs: Array = response.get("bot_actions",[])
	state = (logs[0].state_before if not logs.is_empty() else response.game).duplicate(true)
	_render_state()
	for j in range(2):
		for i in range(6):
			var card: Node2D = hole_cards[i][j]
			card.position = Vector2(640,245)
			card.vacant = false
			card.visible = true
			card.queue_redraw()
			var tween := create_tween()
			tween.tween_property(card,"position",_card_target(i,j),0.18*speed).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
			_tick()
			await tween.finished
	for j in range(2):
		await hole_cards[0][j].reveal(str(state.players[0].hole_cards[j]),0.25*speed)
	await _play_response(response)

func _play_response(response: Dictionary) -> void:
	busy = true
	_lock_actions()
	for log in response.get("bot_actions",[]):
		await _transition(log.state_before)
		status.text = "%s is thinking..." % log.player_name
		active_progress = 0.0
		var timer := create_tween()
		timer.tween_property(self,"active_progress",1.0,0.85*speed)
		await timer.finished
		await _animate_action(log.player_id,log.action,log.state_after)
		await _transition(log.state_after)
	await _transition(response.game)
	active_progress = 0.0
	busy = false
	_render_state()
	if state.street == "complete":
		await _finish_hand()

func _transition(target: Dictionary) -> void:
	# These nodes persist for the whole hand. Only the server supplies card identities.
	for i in range(target.board.size()):
		var card: Node2D = board_cards[i]
		if card.code != "" and card.code != str(target.board[i]):
			push_error("The server changed an already revealed board card")
			return
		if card.code == "":
			status.text = "Dealing the %s..." % ("flop" if i<3 else "turn" if i==3 else "river")
			_tick()
			await card.reveal(str(target.board[i]),0.35*speed)
			await get_tree().create_timer(0.18*speed).timeout
	state = target.duplicate(true)
	if not str(state.street) in observed_streets:
		observed_streets.append(str(state.street))
	_render_state()

func _animate_action(player_id: String, action: String, target: Dictionary) -> void:
	var index := int(player_id.trim_prefix("p"))
	last_actions[player_id] = action.replace("_"," ").to_upper()
	status.text = "%s: %s" % [target.players[index].name,last_actions[player_id]]
	seat_status[index].text = last_actions[player_id]
	if action == "fold":
		var tween := create_tween().set_parallel()
		for card in hole_cards[index]:
			tween.tween_property(card,"modulate:a",0.55,0.35*speed)
			tween.tween_property(card,"rotation",-0.08,0.35*speed)
			tween.tween_property(card,"position",card.position+Vector2(0,8),0.35*speed)
		await tween.finished
	elif action != "check":
		chip_visible = true
		chip_position = BETS[index]
		var tween := create_tween()
		tween.tween_property(self,"chip_position",Vector2(640,295),0.45*speed).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
		_tick()
		await tween.finished
		chip_visible = false
	await get_tree().create_timer(0.22*speed).timeout

func _render_state() -> void:
	if state.is_empty(): return
	queue_redraw()
	var awards := _awards()
	var awarded := 0
	for amount in awards.values(): awarded += int(amount)
	pot.text = "AWARDED $%d" % awarded if state.street == "complete" else "POT  $%d" % state.pot
	street.text = str(state.street).to_upper() if state.street != "complete" else "HAND COMPLETE"
	for i in range(6):
		var player: Dictionary = state.players[i]
		seat_names[i].text = player.name
		seat_stacks[i].text = "$%d" % player.stack
		seat_totals[i].text = "IN HAND $%d" % player.total_committed
		seat_status[i].text = "FOLDED" if player.folded else "ALL IN" if player.all_in else last_actions.get(player.id,"")
		if state.street == "complete" and not player.folded:
			seat_status[i].text = str(state.get("showdown",{}).get(player.id,"WINNER"))
		seat_badges[i].text = "D" if state.button_player_id == player.id else "SB" if state.small_blind_player_id == player.id else "BB" if state.big_blind_player_id == player.id else ""
		for label in [seat_names[i],seat_stacks[i],seat_totals[i]]:
			label.modulate.a = 0.60 if player.folded else 1.0
		bet_labels[i].text = "$%d" % player.current_bet if player.current_bet>0 and state.street != "complete" else ""
	turn.text = "YOUR TURN" if state.get("current_player_id") == "p0" and not busy else ""
	seat_status[0].visible = turn.text.is_empty()
	_lock_actions()
	if not busy and state.street != "complete":
		var details: Dictionary = state.legal_action_details
		status.text = "Your move  /  %s" % ("Free to check" if details.can_check else "$%d to call" % details.call_amount)
		call_button.text = "CHECK" if details.can_check else "CALL $%d" % details.call_amount
		raise_slider.min_value = details.minimum_raise_to if details.can_raise else details.minimum_bet
		raise_slider.max_value = max(raise_slider.min_value,details.maximum_raise_to)
		raise_slider.value = raise_slider.min_value
		_update_raise_text()

func _lock_actions() -> void:
	var playable: bool = not busy and not state.is_empty() and state.get("current_player_id") == "p0"
	var details: Dictionary = state.get("legal_action_details",{})
	fold.disabled = not playable or not details.get("can_fold",false)
	call_button.disabled = not playable or not (details.get("can_call",false) or details.get("can_check",false))
	raise_button.disabled = not playable or not (details.get("can_raise",false) or details.get("can_bet",false) or details.get("can_all_in",false))
	raise_slider.editable = playable and (details.get("can_raise",false) or details.get("can_bet",false))
	for i in range(presets.size()):
		presets[i].disabled = not playable or (not details.get("can_all_in",false) if i==4 else not raise_slider.editable)
	next_button.disabled = busy or state.get("street","") != "complete"
	review_button.visible = not busy and state.get("street","") == "complete"

func _update_raise_text() -> void:
	if state.is_empty(): return
	var details: Dictionary = state.legal_action_details
	raise_caption.text = "RAISE TO $%d   /   MIN $%d - MAX $%d" % [raise_slider.value,raise_slider.min_value,details.maximum_raise_to]
	raise_button.text = "%s $%d" % ["BET" if details.can_bet else "RAISE TO",raise_slider.value]
	if not details.can_raise and not details.can_bet and details.can_all_in:
		raise_button.text = "ALL IN $%d" % details.all_in_amount

func _preset(index: int) -> void:
	if busy: return
	if index == 4:
		raise_slider.value = state.legal_action_details.maximum_raise_to
		raise_button.text = "ALL IN $%d" % state.legal_action_details.all_in_amount
	else:
		var fraction: float = [1.0/3,0.5,0.75,1.0][index]
		raise_slider.value = clampf(state.current_bet + (state.pot+state.legal_action_details.call_amount)*fraction,raise_slider.min_value,raise_slider.max_value)

func _call() -> void:
	await _act("check" if state.legal_action_details.can_check else "call")

func _raise() -> void:
	var details: Dictionary = state.legal_action_details
	if raise_button.text.begins_with("ALL IN"):
		await _act("all_in")
	else:
		await _act("bet" if details.can_bet else "raise",int(raise_slider.value))

func _act(action: String, amount := 0) -> void:
	if busy or state.is_empty(): return
	busy = true
	_lock_actions()
	status.text = "Sending your %s..." % action.replace("_"," ")
	var response: Dictionary = await api.send("/api/game/%s/action" % state.id,{"action":action,"amount":amount})
	if _failed(response): return
	await _animate_action("p0",action,response.game)
	await _play_response(response)

func _finish_hand() -> void:
	busy = true
	_lock_actions()
	for i in range(1,6):
		if state.players[i].folded: continue
		for j in range(2):
			if not hole_cards[i][j].face_up:
				await hole_cards[i][j].reveal(str(state.players[i].hole_cards[j]),0.28*speed)
	var names: Array[String] = []
	var awards := _awards()
	for id in state.winners:
		var index := int(str(id).trim_prefix("p"))
		names.append("%s +$%d" % [state.players[index].name,awards.get(id,0)])
		for card in hole_cards[index]:
			card.highlighted = true
			card.queue_redraw()
	status.text = " / ".join(names)
	status.tooltip_text = status.text
	await get_tree().create_timer(1.2*speed).timeout
	for id in state.winners:
		chip_visible = true
		chip_position = Vector2(640,295)
		var tween := create_tween()
		tween.tween_property(self,"chip_position",SEATS[int(str(id).trim_prefix("p"))],0.6*speed)
		await tween.finished
		chip_visible = false
	review_data = await api.send("/api/game/%s/review" % state.id)
	busy = false
	_lock_actions()
	await get_tree().create_timer(0.8*speed).timeout
	_show_review()

func _failed(response: Dictionary) -> bool:
	if not response.has("error"): return false
	status.text = response.error
	if test_mode: push_error(str(response.error))
	status.tooltip_text = response.error
	busy = true
	reconnect.visible = true
	_lock_actions()
	return true

func _awards() -> Dictionary:
	var result: Dictionary = {}
	for side_pot in state.get("side_pots",[]):
		var winners: Array = side_pot.winner_ids
		if winners.is_empty(): continue
		var share := int(side_pot.amount) / winners.size()
		var remainder := int(side_pot.amount) % winners.size()
		for i in range(winners.size()):
			result[winners[i]] = int(result.get(winners[i],0)) + share + (1 if i<remainder else 0)
	return result

func _recover() -> void:
	reconnect.visible = false
	if state.is_empty():
		await _new_hand()
		return
	var response: Dictionary = await api.send("/api/game/%s" % state.id)
	if _failed(response): return
	await _play_response(response)

func _build_review() -> void:
	review_layer = Control.new()
	review_layer.size = Vector2(1280,800)
	add_child(review_layer)
	var shade := ColorRect.new()
	shade.color = Color(0.015,0.035,0.04,0.88)
	shade.size = Vector2(1280,800)
	review_layer.add_child(shade)
	var panel := Panel.new()
	panel.position = Vector2(244,100)
	panel.size = Vector2(792,600)
	panel.add_theme_stylebox_override("panel",_box(Color("142a2b"),GOLD))
	review_layer.add_child(panel)
	_label("THE COACH'S NOTEBOOK",Rect2(276,124,650,42),36,GOLD,false,review_layer)
	_button("X",Rect2(958,124,46,38),func(): review_layer.hide(),false,review_layer).tooltip_text = "Return to the table"
	review_text = RichTextLabel.new()
	review_text.position = Vector2(280,190)
	review_text.size = Vector2(720,420)
	review_text.bbcode_enabled = true
	review_text.add_theme_font_size_override("normal_font_size",26)
	review_text.add_theme_color_override("default_color",TEXT)
	review_layer.add_child(review_text)
	_button("BACK TO TABLE",Rect2(280,636,260,40),func(): review_layer.hide(),true,review_layer)
	_label("Play. Reflect. Try again.",Rect2(580,636,420,40),23,MUTED,true,review_layer)
	review_layer.hide()

func _show_review() -> void:
	if review_data.has("error"):
		review_data = await api.send("/api/game/%s/review" % state.id)
	if review_data.is_empty() or review_data.has("error"):
		review_text.text = "The review could not be loaded. Return to the table and open Hand Review to try again."
	else:
		var lines: Array[String] = ["[color=#eac568]HAND %02d  /  %d decisions[/color]" % [hand_number,review_data.decisions],"","This is a practice note, not a grade. A good decision can still lose a hand.",""]
		if review_data.decisions < 10:
			lines.append("A few decisions cannot establish your playing style yet.")
		lines.append("\n[color=#eac568]ONE THING TO PRACTICE[/color]")
		for item in review_data.get("next_steps",[]).slice(0,1): lines.append(str(item))
		lines.append("\n[color=#eac568]WHAT WE NOTICED[/color]")
		for item in review_data.get("leaks",[]).slice(0,2): lines.append(str(item))
		lines.append("\n[color=#eac568]THE MATH, IN PLAIN ENGLISH[/color]")
		var decisions: Array = review_data.get("decision_log",[])
		if not decisions.is_empty():
			var decision: Dictionary = decisions[-1]
			lines.append("On the %s, you chose to %s." % [decision.street,str(decision.action).replace("_"," ")])
			lines.append("Your estimated share of the pot was about %d%% against random possible hands. This is an estimate, not knowledge of their cards." % roundi(decision.equity*100))
			if decision.pot_odds>0:
				lines.append("The call needed about %d%% to break even if no more money went in. Later bets and opponents' choices can change that." % roundi(decision.pot_odds*100))
			else:
				lines.append("You did not have to pay to stay in. Checking keeps you in the hand for free.")
		lines.append("\n[color=#a7b8b6]Feedback uses simulated odds and a rule-based reference strategy. A trained coaching model is planned.[/color]")
		review_text.text = "\n".join(lines)
	review_text.scroll_to_line(0)
	review_layer.show()

func _show_help() -> void:
	review_text.text = "[color=#eac568]POKER BASICS[/color]\n\nMake the best five-card hand using your two cards and the five shared cards.\n\nFOLD: Leave this hand. Chips already put in stay in the pot.\n\nCHECK: Stay in for free when nobody has bet more than you.\n\nCALL: Match the bet to stay in.\n\nRAISE: Increase the total bet. Others must call, raise, or fold.\n\nThe flop adds 3 shared cards. The turn adds 1, then the river adds 1. There is betting between each reveal.\n\nAfter the hand, open the notebook to reflect on your choices."
	review_text.scroll_to_line(0)
	review_layer.show()

func _toggle_speed() -> void:
	speed = 1.5 if speed == 1.0 else 1.0
	for child in get_children():
		if child is Button and child.text.begins_with("PACE"):
			child.text = "PACE SLOW" if speed == 1.5 else "PACE 1x"

func _toggle_sound() -> void:
	muted = not muted
	for child in get_children():
		if child is Button and child.text.begins_with("SOUND"):
			child.text = "SOUND OFF" if muted else "SOUND ON"

func _fullscreen() -> void:
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if DisplayServer.window_get_mode()==DisplayServer.WINDOW_MODE_FULLSCREEN else DisplayServer.WINDOW_MODE_FULLSCREEN)

func _build_sound() -> void:
	sound = AudioStreamPlayer.new()
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_8_BITS
	wav.mix_rate = 22050
	var data := PackedByteArray()
	for i in range(900):
		var sample := int(sin(i*0.31)*22.0*(1.0-i/900.0))
		data.append(sample & 255)
	wav.data = data
	sound.stream = wav
	sound.volume_db = -15
	add_child(sound)

func _tick() -> void:
	if not muted and not test_mode: sound.play()

func _smoke() -> void:
	var actions := 0
	if state.is_empty():
		get_tree().quit(1)
		return
	if "--smoke-fold" in OS.get_cmdline_user_args():
		await _act("fold")
		assert(state.street == "complete" and state.players[0].folded)
		assert(not review_data.is_empty())
		print("SMOKE PASS: hero folded, remaining bots finished, review loaded")
		get_tree().quit()
		return
	while not state.is_empty() and state.street != "complete" and actions<80:
		if busy:
			push_error("Smoke test stalled")
			get_tree().quit(1)
			return
		for i in range(state.board.size()):
			assert(board_cards[i].face_up and board_cards[i].code == state.board[i])
		await _call()
		actions += 1
	if state.get("street") != "complete" or review_data.is_empty():
		get_tree().quit(1)
		return
	for i in range(state.board.size()):
		assert(board_cards[i].face_up and board_cards[i].code == state.board[i])
	assert(observed_streets == ["preflop","flop","turn","river","complete"])
	var total_stacks := 0
	var total_committed := 0
	for player in state.players:
		total_stacks += int(player.stack)
		total_committed += int(player.total_committed)
	var total_awarded := 0
	for amount in _awards().values(): total_awarded += int(amount)
	assert(total_stacks == 6000 and total_committed == total_awarded and int(state.pot)==0)
	print("SMOKE PASS: %d actions, %d persistent board cards, review loaded" % [actions,state.board.size()])
	get_tree().quit()
