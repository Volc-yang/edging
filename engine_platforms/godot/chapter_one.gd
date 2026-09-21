extends Node3D

const SPIRIT_COLORS := {
	"heaven": Color("d9d5c7"), "earth": Color("8ebf78"),
	"water": Color("3c8fbc"), "fire": Color("e95b45"),
	"thunder": Color("f2ca52"), "wind": Color("76c8b0"),
	"mountain": Color("7d8790"), "lake": Color("b777a8")
}
const PLAYER_ACTIONS := ["ascend", "receive", "flow", "illuminate", "awaken", "adapt", "stabilize", "exchange"]

var snapshot: Dictionary = {}
var spirit_root: Node3D
var status_label: Label
var decision_label: Label
var detail_label: Label
var selected_slug := ""
var action_selector: OptionButton
var intensity_slider: HSlider
var expression_input: LineEdit
var interface_font: Font


func _ready() -> void:
	interface_font = load_interface_font()
	build_environment()
	build_interface()
	load_snapshot()


func load_interface_font() -> Font:
	var font_file := FontFile.new()
	if font_file.load_dynamic_font("/System/Library/Fonts/Hiragino Sans GB.ttc") == OK:
		return font_file
	var fallback := SystemFont.new()
	fallback.font_names = PackedStringArray(["Hiragino Sans GB", "Arial Unicode MS"])
	return fallback


func build_environment() -> void:
	var world_environment := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("080b10")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("9eb5c7")
	environment.ambient_light_energy = 0.7
	world_environment.environment = environment
	add_child(world_environment)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-52, -28, 0)
	light.light_energy = 1.3
	light.shadow_enabled = true
	add_child(light)

	var camera := Camera3D.new()
	camera.position = Vector3(0, 7.8, 12.5)
	add_child(camera)
	camera.look_at(Vector3.ZERO)

	spirit_root = Node3D.new()
	spirit_root.name = "Spirits"
	add_child(spirit_root)

	var center := MeshInstance3D.new()
	var center_mesh := SphereMesh.new()
	center_mesh.radius = 0.72
	center_mesh.height = 1.44
	center.mesh = center_mesh
	center.material_override = material(Color("f1eee5"), 1.7)
	add_child(center)

	var center_label := Label3D.new()
	center_label.font = interface_font
	center_label.text = "EDGE\n中宫"
	center_label.font_size = 46
	center_label.position = Vector3(0, 1.35, 0)
	center_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(center_label)


func build_interface() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var interface_theme := Theme.new()
	interface_theme.default_font = interface_font
	root.theme = interface_theme
	layer.add_child(root)

	var title := Label.new()
	title.text = "EDGE WORLD  /  第一章 · 万物有灵"
	title.position = Vector2(34, 28)
	title.add_theme_font_size_override("font_size", 26)
	root.add_child(title)

	status_label = Label.new()
	status_label.position = Vector2(36, 70)
	status_label.add_theme_color_override("font_color", Color("9aa7b2"))
	root.add_child(status_label)

	var panel := PanelContainer.new()
	panel.position = Vector2(1010, 26)
	panel.size = Vector2(395, 770)
	root.add_child(panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 16)
	panel.add_child(stack)

	var heading := Label.new()
	heading.text = "玩家介入 · 后天演化"
	heading.add_theme_font_size_override("font_size", 20)
	stack.add_child(heading)
	action_selector = OptionButton.new()
	for action in PLAYER_ACTIONS:
		action_selector.add_item(action)
	action_selector.select(4)
	stack.add_child(action_selector)
	intensity_slider = HSlider.new()
	intensity_slider.min_value = 0.1
	intensity_slider.max_value = 1.0
	intensity_slider.step = 0.1
	intensity_slider.value = 0.7
	stack.add_child(intensity_slider)
	expression_input = LineEdit.new()
	expression_input.text = "玩家进入世界并尝试唤醒眼前之物。"
	expression_input.placeholder_text = "玩家如何介入"
	stack.add_child(expression_input)
	decision_label = Label.new()
	decision_label.custom_minimum_size = Vector2(355, 200)
	decision_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(decision_label)

	var refresh := Button.new()
	refresh.text = "由本地 Ollama 推演下一轮"
	refresh.pressed.connect(run_ollama_and_reload)
	stack.add_child(refresh)

	var offline := Button.new()
	offline.text = "执行确定性规则回退"
	offline.pressed.connect(run_offline_and_reload)
	stack.add_child(offline)

	var separator := HSeparator.new()
	stack.add_child(separator)
	var details_heading := Label.new()
	details_heading.text = "灵体状态"
	details_heading.add_theme_font_size_override("font_size", 18)
	stack.add_child(details_heading)
	detail_label = Label.new()
	detail_label.custom_minimum_size = Vector2(355, 330)
	detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(detail_label)


func snapshot_path() -> String:
	# Every consumer (Godot, UE5, the parity gate) resolves the approved
	# snapshot through EDGEWORLD_CHAPTER_ONE_JSON when it is set, so an
	# external harness can point them all at the same file. Without it the
	# project-relative default is used.
	var override := OS.get_environment("EDGEWORLD_CHAPTER_ONE_JSON")
	if override != "":
		return override
	return ProjectSettings.globalize_path("res://../../models/chapter_one_snapshot.json")


func python_executable() -> String:
	# Prefer the project virtualenv: the system python may lack the declared
	# dependencies in requirements.txt.
	var venv_python := repository_root().path_join(".venv/bin/python")
	if FileAccess.file_exists(venv_python):
		return venv_python
	return "/usr/bin/python3"


func repository_root() -> String:
	return ProjectSettings.globalize_path("res://../..")


func load_snapshot() -> void:
	if not FileAccess.file_exists(snapshot_path()):
		status_label.text = "未找到快照，正在执行离线第一章规则..."
		run_runtime(true)
		return
	var file := FileAccess.open(snapshot_path(), FileAccess.READ)
	var parsed = JSON.parse_string(file.get_as_text())
	if not parsed is Dictionary:
		status_label.text = "快照格式错误"
		return
	snapshot = parsed
	if not validate_snapshot_contract():
		return
	rebuild_spirits()
	update_hud()


func validate_snapshot_contract() -> bool:
	if snapshot.get("schema_version", "") != "edgeworld.chapter-one-snapshot.v2":
		status_label.text = "不支持的快照版本"
		push_error(status_label.text)
		return false
	if snapshot.get("spirits", []).size() != 8:
		status_label.text = "第一章必须包含八个灵体"
		push_error(status_label.text)
		return false
	var cosmology: Dictionary = snapshot.get("cosmology", {})
	if cosmology.get("world_order", "") != "xiantian_bagua" or cosmology.get("change_order", "") != "houtian_bagua":
		status_label.text = "先天世界/后天变化契约不成立"
		push_error(status_label.text)
		return false
	return true


func rebuild_spirits() -> void:
	for child in spirit_root.get_children():
		child.queue_free()
	var spirits: Array = snapshot.get("spirits", [])
	var world_response: Dictionary = snapshot.get("world_response", {})
	var control: Dictionary = world_response.get("control", {})
	var controlled_slug: String = control.get("target_spirit", "")
	for index in spirits.size():
		var spirit: Dictionary = spirits[index]
		var slug: String = spirit.get("slug", "unknown")
		var angle := TAU * float(index) / float(max(spirits.size(), 1)) - PI / 2.0
		var body := StaticBody3D.new()
		body.name = slug
		body.position = Vector3(cos(angle) * 4.4, sin(float(index) * 0.8) * 0.35, sin(angle) * 4.4)
		if slug == controlled_slug:
			body.position.y += float(control.get("vertical_offset", 0.0))
			body.scale = Vector3.ONE * float(control.get("scale_multiplier", 1.0))
		body.input_event.connect(_on_spirit_input.bind(slug))
		spirit_root.add_child(body)

		var mesh_instance := MeshInstance3D.new()
		var mesh := SphereMesh.new()
		mesh.radius = 0.56
		mesh.height = 1.12
		mesh_instance.mesh = mesh
		var emission := 0.8
		if slug == controlled_slug:
			emission *= float(control.get("emission_multiplier", 1.0))
		mesh_instance.material_override = material(SPIRIT_COLORS.get(slug, Color.WHITE), emission)
		body.add_child(mesh_instance)

		var collision := CollisionShape3D.new()
		var shape := SphereShape3D.new()
		shape.radius = 0.62
		collision.shape = shape
		body.add_child(collision)

		var label := Label3D.new()
		label.font = interface_font
		label.text = "%s  %s\n%s" % [spirit.get("symbol", ""), spirit.get("trigram_name", ""), slug]
		if slug == controlled_slug:
			label.text += "\n%s %.2f" % [control.get("effect_cn", "世界响应"), float(control.get("magnitude", 0.0))]
		label.position = Vector3(0, 1.05, 0)
		label.font_size = 38
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		body.add_child(label)


func material(color: Color, emission_energy: float) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.metallic = 0.25
	result.roughness = 0.28
	result.emission_enabled = true
	result.emission = color * 0.42
	result.emission_energy_multiplier = emission_energy
	return result


func update_hud() -> void:
	var validation: Dictionary = snapshot.get("validation", {})
	var cycle: Dictionary = snapshot.get("cycle", {})
	var decision: Dictionary = snapshot.get("decision", {})
	var proposal: Dictionary = decision.get("decision", {})
	var cosmology: Dictionary = snapshot.get("cosmology", {})
	var xiantian: Dictionary = cosmology.get("xiantian_world", {})
	var transition: Dictionary = cosmology.get("houtian_transition", {})
	var encounter: Dictionary = snapshot.get("encounter", {})
	var primary: Dictionary = encounter.get("primary_hexagram", {})
	var changed: Dictionary = encounter.get("changed_hexagram", {})
	var governing_line: Dictionary = encounter.get("governing_line", {})
	var world_response: Dictionary = snapshot.get("world_response", {})
	var forecast: Dictionary = world_response.get("forecast", {})
	var feedback: Dictionary = world_response.get("feedback", {})
	var presentation: Dictionary = snapshot.get("presentation", {})
	status_label.text = "第 %d 轮  ·  先天 %s%s  ·  后天 %s/%s  ·  规则 %.2f  ·  中宫 %.4f" % [
		int(snapshot.get("tick", 1)),
		xiantian.get("symbol", ""), xiantian.get("trigram_name", ""),
		transition.get("focus_spirit", ""), transition.get("direction", ""),
		float(validation.get("score", 0.0)),
		float(cycle.get("final_integrity", 0.0))
	]
	decision_label.text = "%s %s  →  %s %s\n动爻 %s · 主导%s\n卦辞：%s\n爻辞：%s\n\n预判：%s\n反馈：%s\n\n来源 %s / %s\n语义压力 %s" % [
		primary.get("symbol", ""), primary.get("name", ""),
		changed.get("symbol", ""), changed.get("name", ""),
		JSON.stringify(encounter.get("changing_positions", [])),
		governing_line.get("name", ""),
		primary.get("judgment", ""), governing_line.get("text", ""),
		forecast.get("tendency", presentation.get("scene", "")),
		feedback.get("message", presentation.get("player_prompt", "")),
		decision.get("source", "unknown"), decision.get("model", "none"),
		JSON.stringify(proposal.get("action_intents", {}))
	]
	print("EDGEWORLD_GODOT_CHAPTER_ONE_VALID schema=%s spirits=%d primary=%s changed=%s houtian=%s/%s/%d" % [
		snapshot.get("schema_version", ""), snapshot.get("spirits", []).size(),
		primary.get("name", ""), changed.get("name", ""),
		transition.get("focus_spirit", ""), transition.get("direction", ""),
		int(transition.get("luoshu_number", 0))
	])
	show_spirit(selected_slug if selected_slug else "thunder")


func show_spirit(slug: String) -> void:
	selected_slug = slug
	for spirit_value in snapshot.get("spirits", []):
		var spirit: Dictionary = spirit_value
		if spirit.get("slug") != slug:
			continue
		var entity: Dictionary = spirit.get("entity", {})
		var signature: Dictionary = entity.get("signature", {})
		detail_label.text = "%s %s  /  %s\n\n%s\n\n意识 %.4f\n自洽 %.4f\n熵 %.4f\n状态 %s\n位置 %s" % [
			spirit.get("symbol", ""), spirit.get("trigram_name", ""), slug,
			spirit.get("description", ""), float(signature.get("consciousness", 0.0)),
			float(signature.get("coherence", 0.0)), float(signature.get("entropy", 0.0)),
			entity.get("status", ""), JSON.stringify(entity.get("region_id", {}))
		]
		return


func _on_spirit_input(_camera: Node, event: InputEvent, _position: Vector3, _normal: Vector3, _shape: int, slug: String) -> void:
	if event is InputEventMouseButton and event.pressed:
		show_spirit(slug)


func run_ollama_and_reload() -> void:
	run_runtime(false)


func run_offline_and_reload() -> void:
	run_runtime(true)


func run_runtime(offline: bool) -> void:
	status_label.text = "正在运行第一章规则与本地决策..."
	var arguments := PackedStringArray([repository_root().path_join("tools/run_chapter_one.py")])
	arguments.append_array(PackedStringArray([
		"--advance",
		"--player-action", PLAYER_ACTIONS[action_selector.selected],
		"--player-intensity", str(intensity_slider.value),
		"--player-expression", expression_input.text,
		# Keep the write target identical to the read target so a harness that
		# redirected the snapshot cannot end up reading one file and writing
		# another.
		"--output", snapshot_path()
	]))
	if offline:
		arguments.append("--offline")
	var output: Array = []
	var exit_code := OS.execute(python_executable(), arguments, output, true)
	if exit_code != 0:
		status_label.text = "运行失败：%s" % "\n".join(output)
		return
	load_snapshot()
