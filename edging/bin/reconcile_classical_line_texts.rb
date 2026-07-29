#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "digest"
require "pathname"
require "yaml"

ROOT = Pathname(__dir__).join("..").expand_path
DOMAIN_DIR = ROOT.join("docs/02-domain-model")
SOURCE_DIR = DOMAIN_DIR.join("sources")
PRIMARY_PATH = SOURCE_DIR.join("freizl-yijing-2.1.0-64gua.json")
CHECK_PATH = SOURCE_DIR.join("pro-vi-iching-0.5.0-lines.json")
OUTPUT_PATH = DOMAIN_DIR.join("classical-line-texts.v0.1.yaml")
PRIMARY_SHA256 = "5720ef8ff7428a487b87dabcb7f6952020312a10349b0bb763f44e8b026b4c7d"
CHECK_SHA256 = "6028d055d1784095b121e73319282ce2b81622e293665b9f31fbff00d1b2154e"

LABEL_PATTERN = /\A(?:初[九六]|[九六][二三四五]|上[九六])[：:，,]?\s*/
COMPARISON_EQUIVALENTS = {
  "乾" => "干", "彙" => "汇", "馮" => "冯", "遺" => "遗", "復" => "复",
  "艱" => "艰", "貞" => "贞", "鄰" => "邻", "歸" => "归", "師" => "师",
  "撝" => "㧑", "豶" => "豮", "餗" => "𫗧", "繻" => "𦈡"
}.freeze

# The simplified source is the display edition. These are demonstrable copy
# defects rather than edition variants: one line was copied from 同人, and one
# complete line was duplicated in place.
CORRECTIONS = {
  [14, 2] => "九二：大车以载，有攸往，无咎。",
  [44, 5] => "九五：以杞包瓜，含章，有陨自天。"
}.freeze

def comparison_text(text)
  normalized = text.sub(LABEL_PATTERN, "").gsub(/[[:punct:]，。；：、“”‘’！？（）《》〈〉·\s]/, "")
  COMPARISON_EQUIVALENTS.each { |source, target| normalized = normalized.gsub(source, target) }
  normalized
end

raise "primary source checksum mismatch" unless Digest::SHA256.file(PRIMARY_PATH).hexdigest == PRIMARY_SHA256
raise "check source checksum mismatch" unless Digest::SHA256.file(CHECK_PATH).hexdigest == CHECK_SHA256

primary = JSON.parse(PRIMARY_PATH.read)
check_payload = JSON.parse(CHECK_PATH.read)
check = check_payload.fetch("hexagrams")

raise "primary source must contain 64 hexagrams" unless primary.size == 64
raise "check source must contain 64 hexagrams" unless check.size == 64

check_by_sequence = check.to_h { |hexagram| [hexagram.fetch("king_wen_index"), hexagram] }
lines = []
differences = []

primary.each_with_index do |hexagram, hexagram_offset|
  king_wen_index = hexagram_offset + 1
  check_hexagram = check_by_sequence.fetch(king_wen_index)
  primary_lines = hexagram.fetch("yao_ci").first(6)
  primary_xiao = hexagram.fetch("xiao_xiang").first(6)
  check_lines = check_hexagram.fetch("lines")

  raise "hexagram #{king_wen_index} must have six primary lines" unless primary_lines.size == 6
  raise "hexagram #{king_wen_index} must have six 小象 entries" unless primary_xiao.size == 6
  raise "hexagram #{king_wen_index} must have six check lines" unless check_lines.size == 6

  primary_lines.each_with_index do |source_text, line_offset|
    line_index = line_offset + 1
    check_line = check_lines.fetch(line_offset)
    check_text = check_line.fetch("simplified")
    normalized_primary = comparison_text(source_text)
    normalized_check = comparison_text(check_text)
    agreement = normalized_primary == normalized_check
    corrected_text = CORRECTIONS.fetch([king_wen_index, line_index], source_text).strip

    unless agreement
      differences << {
        "id" => format("proto_hex_%02d_line_%d", king_wen_index, line_index),
        "primary_text" => source_text.strip,
        "check_text" => check_text.strip,
        "resolution" => CORRECTIONS.key?([king_wen_index, line_index]) ? "objective_copy_defect_corrected" : "primary_edition_retained"
      }
    end

    lines << {
      "id" => format("proto_hex_%02d_line_%d", king_wen_index, line_index),
      "king_wen_index" => king_wen_index,
      "hexagram_name_cn" => hexagram.fetch("name"),
      "line_index" => line_index,
      "text" => corrected_text.sub(LABEL_PATTERN, "").strip,
      "commentary" => "《象》曰：#{primary_xiao.fetch(line_offset).strip}",
      "source_status" => agreement ? "dual_source_normalized_agreement" : "reviewed_variant",
      "resolution" => if agreement
        "sources_agree_after_simplification_and_punctuation_normalization"
      elsif CORRECTIONS.key?([king_wen_index, line_index])
        "objective_copy_defect_corrected_from_check_source"
      else
        "primary_simplified_edition_retained"
      end
    }
  end
end

raise "expected 384 canonical lines" unless lines.size == 384
raise "canonical line text retains leading punctuation" if lines.any? { |line| line.fetch("text").match?(/\A[，,：:；;]/) }
raise "expected 20 reviewed source differences, got #{differences.size}" unless differences.size == 20
raise "expected exactly two objective corrections" unless CORRECTIONS.keys.all? do |hexagram_index, line_index|
  lines.find { |line| line.fetch("king_wen_index") == hexagram_index && line.fetch("line_index") == line_index }
end

payload = {
  "version" => "0.1",
  "edition_policy" => "Use the simplified primary edition; retain textual variants; correct only demonstrable copy defects.",
  "sources" => check_payload.fetch("sources"),
  "line_count" => lines.size,
  "normalized_agreement_count" => lines.count { |line| line.fetch("source_status") == "dual_source_normalized_agreement" },
  "reviewed_variant_count" => differences.size,
  "objective_correction_count" => CORRECTIONS.size,
  "differences" => differences,
  "lines" => lines
}

OUTPUT_PATH.write(YAML.dump(payload))
warn "Wrote #{lines.size} canonical lines: #{payload.fetch('normalized_agreement_count')} agreements, #{differences.size} reviewed variants."
