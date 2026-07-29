#!/usr/bin/env ruby
# frozen_string_literal: true

require "pathname"
require "json"
require "digest"
require "yaml"

ROOT = Pathname(__dir__).join("..").expand_path
DOMAIN_DIR = ROOT.join("docs/02-domain-model")
SOURCE_DIR = DOMAIN_DIR.join("sources")
PRIMARY_NAME_EQUIVALENTS = { "遯" => "遁" }.freeze
EIGHT_PALACES = {
  "乾" => %w[乾 姤 遁 否 观 剥 晋 大有],
  "坎" => %w[坎 节 屯 既济 革 丰 明夷 师],
  "艮" => %w[艮 贲 大畜 损 睽 履 中孚 渐],
  "震" => %w[震 豫 解 恒 升 井 大过 随],
  "巽" => %w[巽 小畜 家人 益 无妄 噬嗑 颐 蛊],
  "离" => %w[离 旅 鼎 未济 蒙 涣 讼 同人],
  "坤" => %w[坤 复 临 泰 大壮 夬 需 比],
  "兑" => %w[兑 困 萃 咸 蹇 谦 小过 归妹]
}.freeze
EIGHT_PALACE_STAGES = [
  ["palace_root", "本宫", []],
  ["first_generation", "一世", [1]],
  ["second_generation", "二世", [1, 2]],
  ["third_generation", "三世", [1, 2, 3]],
  ["fourth_generation", "四世", [1, 2, 3, 4]],
  ["fifth_generation", "五世", [1, 2, 3, 4, 5]],
  ["wandering_soul", "游魂", [1, 2, 3, 5]],
  ["returning_soul", "归魂", [5]]
].freeze

def load_yaml(path)
  YAML.safe_load(path.read, aliases: true)
end

def assert(condition, message)
  raise message unless condition
end

hexagrams = load_yaml(DOMAIN_DIR.join("hexagram-spacetime.v0.1.yaml")).fetch("hexagrams")
line_basis = load_yaml(DOMAIN_DIR.join("line-structures.v0.1.yaml")).fetch("lines")
classical_data = load_yaml(DOMAIN_DIR.join("classical-line-texts.v0.1.yaml"))
classical_lines = classical_data.fetch("lines")
confirmed_data = load_yaml(DOMAIN_DIR.join("confirmed-line-abstractions.v0.1.yaml"))
confirmed = confirmed_data.fetch("abstractions")
eight_palace_memberships = confirmed_data.fetch("eight_palace_memberships")
returning_soul_changes = confirmed_data.fetch("returning_soul_changes")
scale_keys = confirmed_data.fetch("scale_anchor_keys")
draft_data = load_yaml(DOMAIN_DIR.join("draft-line-abstractions.v0.1.yaml"))
drafts = draft_data.fetch("abstractions")

source_registry = confirmed_data.fetch("source_registry")
primary_source = source_registry.fetch("primary_display_edition")
check_source = source_registry.fetch("independent_check_edition")
primary_path = DOMAIN_DIR.join(primary_source.fetch("file"))
check_path = DOMAIN_DIR.join(check_source.fetch("file"))
primary_payload = JSON.parse(primary_path.read)
check_payload = JSON.parse(check_path.read)

def resolve_json_pointer(payload, pointer)
  return payload if pointer.empty?

  pointer.split("/").drop(1).reduce(payload) do |value, token|
    key = token.gsub("~1", "/").gsub("~0", "~")
    value.is_a?(Array) ? value.fetch(Integer(key, 10)) : value.fetch(key)
  end
end

def validate_source_correspondence(entry, line, classical, primary_payload, check_payload)
  id = entry.fetch("id")
  source = entry.fetch("source_correspondence")
  canonical = source.fetch("canonical")
  primary = source.fetch("primary_display_edition")
  check = source.fetch("independent_check_edition")
  hexagram_offset = line.fetch("king_wen_index") - 1
  line_offset = line.fetch("line_index") - 1

  assert(canonical.fetch("record_id") == id, "#{id} canonical source id mismatch")
  assert(canonical.fetch("source_status") == classical.fetch("source_status"), "#{id} canonical source status mismatch")
  assert(canonical.fetch("resolution") == classical.fetch("resolution"), "#{id} canonical source resolution mismatch")
  assert(primary.fetch("king_wen_index") == line.fetch("king_wen_index"), "#{id} primary source hexagram mismatch")
  assert(primary.fetch("line_index") == line.fetch("line_index"), "#{id} primary source line mismatch")
  assert(primary.fetch("line_json_pointer") == "/#{hexagram_offset}/yao_ci/#{line_offset}", "#{id} primary line pointer mismatch")
  assert(primary.fetch("commentary_json_pointer") == "/#{hexagram_offset}/xiao_xiang/#{line_offset}", "#{id} primary commentary pointer mismatch")
  primary_name = primary_payload.fetch(hexagram_offset).fetch("name")
  normalized_primary_name = PRIMARY_NAME_EQUIVALENTS.fetch(primary_name, primary_name)
  assert(normalized_primary_name == line.fetch("hexagram_name_cn"), "#{id} primary source hexagram name mismatch")
  assert(resolve_json_pointer(primary_payload, primary.fetch("line_json_pointer")).is_a?(String), "#{id} primary line pointer is unresolved")
  assert(resolve_json_pointer(primary_payload, primary.fetch("commentary_json_pointer")).is_a?(String), "#{id} primary commentary pointer is unresolved")
  assert(check.fetch("king_wen_index") == line.fetch("king_wen_index"), "#{id} check source hexagram mismatch")
  assert(check.fetch("line_index") == line.fetch("line_index"), "#{id} check source line mismatch")
  assert(check.fetch("line_json_pointer") == "/hexagrams/#{hexagram_offset}/lines/#{line_offset}", "#{id} check line pointer mismatch")
  assert(check.fetch("commentary_json_pointer") == "/hexagrams/#{hexagram_offset}/commentaries/#{line_offset}", "#{id} check commentary pointer mismatch")
  check_hexagram = check_payload.fetch("hexagrams").fetch(hexagram_offset)
  assert(check_hexagram.fetch("king_wen_index") == line.fetch("king_wen_index"), "#{id} check payload sequence mismatch")
  check_names = [check_hexagram.fetch("name_traditional"), check_hexagram.fetch("name_simplified")].map do |name|
    PRIMARY_NAME_EQUIVALENTS.fetch(name, name)
  end
  assert(check_names.include?(line.fetch("hexagram_name_cn")), "#{id} check source hexagram name mismatch")
  assert(resolve_json_pointer(check_payload, check.fetch("line_json_pointer")).is_a?(Hash), "#{id} check line pointer is unresolved")
  assert(resolve_json_pointer(check_payload, check.fetch("commentary_json_pointer")).is_a?(Hash), "#{id} check commentary pointer is unresolved")
end

assert(hexagrams.size == 64, "expected 64 hexagrams")
assert(line_basis.size == 384, "expected 384 lines")
assert(classical_lines.size == 384, "expected 384 canonical classical lines")
assert(classical_data.fetch("normalized_agreement_count") == 364, "expected 364 dual-source agreements")
assert(classical_data.fetch("reviewed_variant_count") == 20, "expected 20 reviewed variants")
assert(classical_data.fetch("objective_correction_count") == 2, "expected two objective source corrections")
assert(draft_data.fetch("source_registry") == source_registry, "draft and confirmed source registries differ")
assert(Digest::SHA256.file(primary_path).hexdigest == primary_source.fetch("sha256"), "primary source checksum mismatch")
assert(Digest::SHA256.file(check_path).hexdigest == check_source.fetch("sha256"), "check source checksum mismatch")
assert(hexagrams.map { |entry| entry.fetch("family_id") }.uniq.size == 64, "family ids must be unique")
assert(hexagrams.map { |entry| entry.dig("square", "coordinate_upper_lower") }.uniq.size == 64, "square coordinates must be unique")
assert(hexagrams.map { |entry| entry.dig("circle_time", "circle_index_qian_origin_clockwise") }.sort == (0...64).to_a, "circle indexes must cover 0..63")
assert(hexagrams.map { |entry| entry.dig("circle_time", "cycle_index_fu_origin") }.sort == (0...64).to_a, "cycle indexes must cover 0..63")
assert(eight_palace_memberships.size == 64, "expected 64 eight-palace memberships")
assert(returning_soul_changes.size == 8, "expected eight wandering-to-returning-soul changes")
assert(line_basis.map { |entry| entry.fetch("id") }.uniq.size == 384, "line ids must be unique")
assert(line_basis.group_by { |entry| entry.fetch("family_id") }.values.all? { |entries| entries.size == 6 }, "every family must have six lines")
assert(classical_lines.map { |entry| entry.fetch("id") }.uniq.size == 384, "canonical classical line ids must be unique")
assert(classical_lines.all? { |entry| !entry.fetch("text").strip.empty? && !entry.fetch("commentary").strip.empty? }, "canonical classical text cannot be empty")
assert(line_basis.all? { |entry| entry.fetch("classical_source_status") != "missing" }, "generated lines cannot have missing classical text")
classical_by_id = classical_lines.to_h { |entry| [entry.fetch("id"), entry] }
line_basis.each do |entry|
  source = classical_by_id.fetch(entry.fetch("id"))
  assert(entry.fetch("classical_text") == source.fetch("text"), "#{entry.fetch('id')} classical text is stale")
  assert(entry.fetch("classical_commentary") == source.fetch("commentary"), "#{entry.fetch('id')} commentary is stale")
  assert(entry.fetch("classical_source_status") == source.fetch("source_status"), "#{entry.fetch('id')} source status is stale")
end

line_by_id = line_basis.to_h { |entry| [entry.fetch("id"), entry] }
hexagram_by_family = hexagrams.to_h { |entry| [entry.fetch("family_id"), entry] }
hexagram_by_name = hexagrams.to_h { |entry| [entry.fetch("name_cn"), entry] }
membership_by_family = eight_palace_memberships.to_h { |entry| [entry.fetch("family_id"), entry] }

assert(membership_by_family.size == 64, "eight-palace membership families must be unique")
EIGHT_PALACES.each do |root_name, names|
  root = hexagram_by_name.fetch(root_name)
  wandering = hexagram_by_name.fetch(names.fetch(6))
  returning = hexagram_by_name.fetch(names.fetch(7))

  names.each_with_index do |name, stage_index|
    source = hexagram_by_name.fetch(name)
    membership = membership_by_family.fetch(source.fetch("family_id"))
    stage_key, stage_cn, changed_from_root = EIGHT_PALACE_STAGES.fetch(stage_index)

    assert(membership.fetch("king_wen_index") == source.fetch("king_wen_index"), "#{membership.fetch('id')} index mismatch")
    assert(membership.fetch("hexagram_name_cn") == name, "#{membership.fetch('id')} name mismatch")
    assert(membership.fetch("palace_root_family_id") == root.fetch("family_id"), "#{membership.fetch('id')} palace family mismatch")
    assert(membership.fetch("palace_root_name_cn") == root_name, "#{membership.fetch('id')} palace name mismatch")
    assert(membership.fetch("palace_stage") == stage_key, "#{membership.fetch('id')} palace stage mismatch")
    assert(membership.fetch("palace_stage_cn") == stage_cn, "#{membership.fetch('id')} Chinese stage mismatch")
    assert(membership.fetch("palace_stage_index") == stage_index, "#{membership.fetch('id')} stage index mismatch")
    assert(membership.fetch("changed_lines_from_palace_root") == changed_from_root, "#{membership.fetch('id')} root change mask mismatch")
    assert(membership.fetch("is_wandering_soul") == (stage_index == 6), "#{membership.fetch('id')} wandering-soul flag mismatch")
    assert(membership.fetch("is_returning_soul") == (stage_index == 7), "#{membership.fetch('id')} returning-soul flag mismatch")
    assert(membership.fetch("associated_wandering_soul_family_id") == wandering.fetch("family_id"), "#{membership.fetch('id')} wandering-soul family mismatch")
    assert(membership.fetch("associated_wandering_soul_name_cn") == wandering.fetch("name_cn"), "#{membership.fetch('id')} wandering-soul name mismatch")
    assert(membership.fetch("associated_returning_soul_family_id") == returning.fetch("family_id"), "#{membership.fetch('id')} returning-soul family mismatch")
    assert(membership.fetch("associated_returning_soul_name_cn") == returning.fetch("name_cn"), "#{membership.fetch('id')} returning-soul name mismatch")
    assert(membership.fetch("returning_soul_target_coordinate_upper_lower") == returning.dig("square", "coordinate_upper_lower"), "#{membership.fetch('id')} returning-soul coordinate mismatch")
    assert(membership.fetch("returning_soul_target_cycle_index_fu_origin") == returning.dig("circle_time", "cycle_index_fu_origin"), "#{membership.fetch('id')} returning-soul cycle mismatch")
    assert(membership.fetch("returning_soul_target_temporal_phase") == returning.dig("circle_time", "phase"), "#{membership.fetch('id')} returning-soul phase mismatch")
  end

  change = returning_soul_changes.find { |entry| entry.fetch("palace_root_family_id") == root.fetch("family_id") }
  assert(!change.nil?, "#{root_name} palace returning-soul change is missing")
  assert(change.fetch("source_family_id") == wandering.fetch("family_id"), "#{root_name} palace wandering-soul source mismatch")
  assert(change.fetch("target_family_id") == returning.fetch("family_id"), "#{root_name} palace returning-soul target mismatch")
  assert(change.fetch("changed_lines") == [1, 2, 3], "#{root_name} palace returning-soul change must flip the lower trigram")
  assert(change.fetch("hamming_distance") == 3, "#{root_name} palace returning-soul Hamming distance mismatch")
  assert(change.fetch("atomic_step_count") == 3, "#{root_name} palace returning-soul atomic count mismatch")
  assert(change.fetch("intermediate_order") == "unspecified", "#{root_name} palace returning-soul order must remain unspecified")
end

required_fields = %w[
  state_name core_abstraction fixed_pattern variable_pattern short_definition
  semantic_anchor stable_path changing_path principle scale_mapping scale_boundary
  source_correspondence review
]

assert(confirmed.map { |entry| entry.fetch("id") }.uniq.size == confirmed.size, "confirmed ids must be unique")

confirmed.each do |entry|
  id = entry.fetch("id")
  assert(line_by_id.key?(id), "#{id} does not exist in the generated line basis")
  line = line_by_id.fetch(id)
  required_fields.each { |field| assert(entry.key?(field), "#{id} is missing #{field}") }
  anchors = entry.fetch("scale_anchors")
  assert(anchors.keys == scale_keys, "#{id} scale anchors must use the declared order and keys")
  assert(anchors.values.all? { |value| value.is_a?(String) && !value.strip.empty? }, "#{id} has an empty scale anchor")
  assert(entry.fetch("stable_path").include?(line.dig("change", "stable_line_value").to_s), "#{id} stable path has the wrong line value")
  assert(entry.fetch("changing_path").include?(line.dig("change", "changing_line_value").to_s), "#{id} changing path has the wrong line value")
  assert(entry.fetch("changing_path").include?(line.dig("change", "target_hexagram_name_cn")), "#{id} changing path has the wrong target hexagram")
  assert(entry.dig("review", "status") == "confirmed", "#{id} is not confirmed")
  validate_source_correspondence(entry, line, classical_by_id.fetch(id), primary_payload, check_payload)
end

assert(draft_data.fetch("scale_anchor_keys") == scale_keys, "draft and confirmed scale keys differ")
assert(drafts.map { |entry| entry.fetch("id") }.uniq.size == drafts.size, "draft ids must be unique")
assert((drafts.map { |entry| entry.fetch("id") } & confirmed.map { |entry| entry.fetch("id") }).empty?, "draft and confirmed ids overlap")

drafts.each do |entry|
  id = entry.fetch("id")
  assert(line_by_id.key?(id), "#{id} does not exist in the generated line basis")
  line = line_by_id.fetch(id)
  required_fields.each { |field| assert(entry.key?(field), "#{id} is missing #{field}") }
  anchors = entry.fetch("scale_anchors")
  assert(anchors.keys == scale_keys, "#{id} draft scale anchors must use the declared order and keys")
  assert(anchors.values.all? { |value| value.is_a?(String) && !value.strip.empty? }, "#{id} has an empty draft scale anchor")
  assert(entry.fetch("stable_path").include?(line.dig("change", "stable_line_value").to_s), "#{id} draft stable path has the wrong line value")
  assert(entry.fetch("changing_path").include?(line.dig("change", "changing_line_value").to_s), "#{id} draft changing path has the wrong line value")
  assert(entry.fetch("changing_path").include?(line.dig("change", "target_hexagram_name_cn")), "#{id} draft changing path has the wrong target hexagram")
  assert(entry.dig("review", "status") == "draft", "#{id} is not draft")
  validate_source_correspondence(entry, line, classical_by_id.fetch(id), primary_payload, check_payload)
end

missing_classical = line_basis.count { |entry| entry.fetch("classical_text").to_s.strip.empty? }

puts "hexagrams: #{hexagrams.size}/64"
puts "line structures: #{line_basis.size}/384"
puts "canonical classical lines: #{classical_lines.size}/384"
puts "dual-source normalized agreements: #{classical_data.fetch('normalized_agreement_count')}/384"
puts "reviewed classical variants: #{classical_data.fetch('reviewed_variant_count')}"
puts "confirmed abstractions: #{confirmed.size}/384"
puts "confirmed scale anchors: #{confirmed.size * scale_keys.size}/#{384 * scale_keys.size}"
puts "confirmed source correspondences: #{confirmed.size}/384"
puts "eight-palace memberships: #{eight_palace_memberships.size}/64"
puts "hexagram wandering-soul associations: #{eight_palace_memberships.size}/64"
puts "hexagram returning-soul associations: #{eight_palace_memberships.size}/64"
puts "wandering-to-returning-soul composite changes: #{returning_soul_changes.size}/8"
puts "draft abstractions: #{drafts.size}"
puts "draft scale anchors: #{drafts.size * scale_keys.size}"
puts "draft source correspondences: #{drafts.size}/#{drafts.size}"
puts "missing classical line texts: #{missing_classical}/384"
puts "structural validation: PASS"

complete = confirmed.size == 384 && drafts.empty?
puts "completion: #{complete ? 'COMPLETE' : 'IN PROGRESS'}"

if ARGV.include?("--complete")
  assert(confirmed.size == 384, "completion requires 384 confirmed abstractions")
  assert(drafts.empty?, "completion requires an empty draft queue")
end
