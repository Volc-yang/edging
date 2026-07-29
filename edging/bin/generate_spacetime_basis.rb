#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"
require "yaml"

ROOT = Pathname(__dir__).join("..").expand_path
DOMAIN_DIR = ROOT.join("docs/02-domain-model")
YIJING_TEXT_PATH = ROOT.join("../engine/yijing_text.json")
CLASSICAL_LINES_PATH = DOMAIN_DIR.join("classical-line-texts.v0.1.yaml")

TRIGRAMS = {
  "111" => { "name_cn" => "乾", "name_en" => "qian", "xiantian_number" => 1 },
  "110" => { "name_cn" => "兑", "name_en" => "dui", "xiantian_number" => 2 },
  "101" => { "name_cn" => "离", "name_en" => "li", "xiantian_number" => 3 },
  "100" => { "name_cn" => "震", "name_en" => "zhen", "xiantian_number" => 4 },
  "011" => { "name_cn" => "巽", "name_en" => "xun", "xiantian_number" => 5 },
  "010" => { "name_cn" => "坎", "name_en" => "kan", "xiantian_number" => 6 },
  "001" => { "name_cn" => "艮", "name_en" => "gen", "xiantian_number" => 7 },
  "000" => { "name_cn" => "坤", "name_en" => "kun", "xiantian_number" => 8 }
}.freeze

# 先天六十四卦圆图：乾在图形顶部，按顺时针方向排列。
CIRCLE_ORDER = %w[
  乾 姤 大过 鼎 恒 巽 井 蛊 升 讼 困 未济 解 涣 坎 蒙
  师 遁 咸 旅 小过 渐 蹇 艮 谦 否 萃 晋 豫 观 比 剥
  坤 复 颐 屯 益 震 噬嗑 随 无妄 明夷 贲 既济 家人 丰 离 革 同人
  临 损 节 中孚 归妹 兑 睽 履 泰 大畜 需 小畜 大壮 大有 夬
].freeze

PHASES = %w[shaoyang taiyang shaoyin taiyin].freeze
LOCAL_LEVELS = %w[lower middle upper].freeze

def load_yaml(path)
  YAML.safe_load(path.read, aliases: false)
end

def line_vector(upper_code, lower_code)
  # Each trigram code is written bottom-to-top. The six-line vector follows
  # the canonical line order: initial line through top line.
  (lower_code.chars + upper_code.chars).map(&:to_i)
end

def phase_for(cycle_index)
  PHASES.fetch(cycle_index / 16)
end

def change_key(key, line_index)
  upper = key[0, 3].chars
  lower = key[3, 3].chars
  target = line_index <= 3 ? lower : upper
  target_index = line_index <= 3 ? line_index - 1 : line_index - 4
  target[target_index] = target[target_index] == "1" ? "0" : "1"
  upper.join + lower.join
end

def trigram_record(code)
  trigram = TRIGRAMS.fetch(code)
  {
    "name_cn" => trigram.fetch("name_cn"),
    "name_en" => trigram.fetch("name_en"),
    "xiantian_number" => trigram.fetch("xiantian_number"),
    "line_code_bottom_to_top" => code
  }
end

families = load_yaml(DOMAIN_DIR.join("hexagram-families.v0.1.yaml")).fetch("families")
family_by_index = families.to_h { |family| [family.fetch("index"), family] }
yijing = JSON.parse(YIJING_TEXT_PATH.read)
classical_lines = load_yaml(CLASSICAL_LINES_PATH).fetch("lines")
classical_line_by_id = classical_lines.to_h { |line| [line.fetch("id"), line] }

raise "Expected 64 hexagrams, got #{yijing.size}" unless yijing.size == 64
raise "Circle order must contain 64 unique names" unless CIRCLE_ORDER.size == 64 && CIRCLE_ORDER.uniq.size == 64

text_by_name = yijing.to_h { |key, value| [value.fetch("name"), [key, value]] }
missing_circle_names = CIRCLE_ORDER.reject { |name| text_by_name.key?(name) }
raise "Unknown circle names: #{missing_circle_names.join(', ')}" unless missing_circle_names.empty?

circle_index_by_name = CIRCLE_ORDER.each_with_index.to_h
cycle_origin = circle_index_by_name.fetch("复")

hexagrams = yijing.map do |key, text|
  sequence = text.fetch("sequence")
  family = family_by_index.fetch(sequence)
  upper_code = key[0, 3]
  lower_code = key[3, 3]
  upper = trigram_record(upper_code)
  lower = trigram_record(lower_code)
  circle_index = circle_index_by_name.fetch(text.fetch("name"))
  cycle_index = (circle_index - cycle_origin) % 64

  {
    "family_id" => family.fetch("id"),
    "king_wen_index" => sequence,
    "name_cn" => text.fetch("name"),
    "symbol" => text.fetch("symbol"),
    "hexagram_key" => key,
    "line_vector_bottom_to_top" => line_vector(upper_code, lower_code),
    "upper_trigram" => upper,
    "lower_trigram" => lower,
    "square" => {
      "coordinate_upper_lower" => [upper.fetch("xiantian_number"), lower.fetch("xiantian_number")],
      "row_top_to_bottom" => 9 - lower.fetch("xiantian_number"),
      "column_left_to_right" => 9 - upper.fetch("xiantian_number")
    },
    "circle_time" => {
      "circle_index_qian_origin_clockwise" => circle_index,
      "cycle_index_fu_origin" => cycle_index,
      "cycle_fraction" => (cycle_index / 64.0).round(6),
      "phase" => phase_for(cycle_index),
      "phase_index" => cycle_index % 16,
      "waxing_direction" => cycle_index <= 31 ? "yang_waxing" : "yin_waxing"
    }
  }
end.sort_by { |entry| entry.fetch("king_wen_index") }

hexagram_by_key = hexagrams.to_h { |entry| [entry.fetch("hexagram_key"), entry] }
text_key_by_sequence = yijing.to_h { |key, text| [text.fetch("sequence"), key] }

lines = hexagrams.flat_map do |hexagram|
  key = text_key_by_sequence.fetch(hexagram.fetch("king_wen_index"))
  text = yijing.fetch(key)
  vector = hexagram.fetch("line_vector_bottom_to_top")
  coordinate = hexagram.dig("square", "coordinate_upper_lower")

  (1..6).map do |line_index|
    polarity = vector.fetch(line_index - 1) == 1 ? "yang" : "yin"
    counterpart = line_index <= 3 ? line_index + 3 : line_index - 3
    target_key = change_key(key, line_index)
    target = hexagram_by_key.fetch(target_key)
    target_coordinate = target.dig("square", "coordinate_upper_lower")
    source_time = hexagram.fetch("circle_time")
    target_time = target.fetch("circle_time")
    line_id = format("proto_hex_%02d_line_%d", hexagram.fetch("king_wen_index"), line_index)
    line_text = classical_line_by_id.fetch(line_id)

    {
      "id" => line_id,
      "family_id" => hexagram.fetch("family_id"),
      "king_wen_index" => hexagram.fetch("king_wen_index"),
      "hexagram_name_cn" => hexagram.fetch("name_cn"),
      "line_index" => line_index,
      "classical_source_status" => line_text.fetch("source_status"),
      "classical_text" => line_text.fetch("text"),
      "classical_commentary" => line_text.fetch("commentary"),
      "classical_source_resolution" => line_text.fetch("resolution"),
      "fixed" => {
        "spatial_coordinate_upper_lower_line" => [coordinate[0], coordinate[1], line_index],
        "polarity" => polarity,
        "realm" => line_index <= 3 ? "lower_trigram" : "upper_trigram",
        "local_level" => LOCAL_LEVELS.fetch((line_index - 1) % 3),
        "central" => [2, 5].include?(line_index),
        "correct_position" => (polarity == "yang" && line_index.odd?) || (polarity == "yin" && line_index.even?),
        "correspondence_line" => counterpart,
        "correspondence_effective" => vector.fetch(line_index - 1) != vector.fetch(counterpart - 1),
        "circle_index_qian_origin_clockwise" => source_time.fetch("circle_index_qian_origin_clockwise"),
        "cycle_index_fu_origin" => source_time.fetch("cycle_index_fu_origin"),
        "temporal_phase" => source_time.fetch("phase"),
        "local_time_stage" => line_index
      },
      "change" => {
        "stable_line_value" => polarity == "yang" ? 7 : 8,
        "changing_line_value" => polarity == "yang" ? 9 : 6,
        "polarity_change" => polarity == "yang" ? "yang_to_yin" : "yin_to_yang",
        "spatial_delta_upper_lower" => [target_coordinate[0] - coordinate[0], target_coordinate[1] - coordinate[1]],
        "target_family_id" => target.fetch("family_id"),
        "target_hexagram_name_cn" => target.fetch("name_cn"),
        "target_coordinate_upper_lower" => target_coordinate,
        "target_circle_index_qian_origin_clockwise" => target_time.fetch("circle_index_qian_origin_clockwise"),
        "target_cycle_index_fu_origin" => target_time.fetch("cycle_index_fu_origin"),
        "target_temporal_phase" => target_time.fetch("phase")
      }
    }
  end
end

raise "Expected 64 generated hexagrams, got #{hexagrams.size}" unless hexagrams.size == 64
raise "Expected 384 generated lines, got #{lines.size}" unless lines.size == 384
raise "Generated line ids are not unique" unless lines.map { |entry| entry.fetch("id") }.uniq.size == 384

lines.each do |line|
  source = hexagrams.find { |entry| entry.fetch("family_id") == line.fetch("family_id") }
  target = hexagrams.find { |entry| entry.fetch("family_id") == line.dig("change", "target_family_id") }
  distance = source.fetch("line_vector_bottom_to_top").zip(target.fetch("line_vector_bottom_to_top")).count { |a, b| a != b }
  raise "#{line.fetch('id')} target is not one line away" unless distance == 1
end

hexagram_payload = {
  "version" => "0.1",
  "coordinate_convention" => "upper_xiantian_number, lower_xiantian_number; lines bottom-to-top",
  "circle_origin" => "qian_at_0_clockwise",
  "cycle_origin" => "fu_at_0",
  "hexagrams" => hexagrams
}

line_payload = {
  "version" => "0.1",
  "generated_from" => ["engine/yijing_text.json", "hexagram-families.v0.1.yaml", "classical-line-texts.v0.1.yaml"],
  "line_count" => lines.size,
  "lines" => lines
}

DOMAIN_DIR.join("hexagram-spacetime.v0.1.yaml").write(YAML.dump(hexagram_payload))
DOMAIN_DIR.join("line-structures.v0.1.yaml").write(YAML.dump(line_payload))

warn "Generated #{hexagrams.size} hexagrams and #{lines.size} line structures."
