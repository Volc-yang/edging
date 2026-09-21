#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"
require "yaml"

ROOT = Pathname(__dir__).join("..").expand_path
DOMAIN_DIR = ROOT.join("docs/02-domain-model")
ENGINE_TEXT_PATH = ROOT.join("../engine/yijing_text.json")
PRIMARY_PATH = DOMAIN_DIR.join("sources/freizl-yijing-2.1.0-64gua.json")
CLASSICAL_LINES_PATH = DOMAIN_DIR.join("classical-line-texts.v0.1.yaml")

existing = JSON.parse(ENGINE_TEXT_PATH.read)
primary = JSON.parse(PRIMARY_PATH.read)
canonical_lines = YAML.safe_load(CLASSICAL_LINES_PATH.read, aliases: false).fetch("lines")

raise "expected 64 engine hexagrams" unless existing.size == 64
raise "expected 64 primary hexagrams" unless primary.size == 64
raise "expected 384 canonical lines" unless canonical_lines.size == 384

primary_by_sequence = primary.each_with_index.to_h { |entry, index| [index + 1, entry] }
lines_by_sequence = canonical_lines.group_by { |line| line.fetch("king_wen_index") }

synced = existing.to_h do |key, current|
  sequence = current.fetch("sequence")
  source = primary_by_sequence.fetch(sequence)
  lines = lines_by_sequence.fetch(sequence).sort_by { |line| line.fetch("line_index") }.map do |line|
    position = line.fetch("line_index")
    lower_to_upper_bits = key[3, 3].chars + key[0, 3].chars
    {
      "line_number" => position,
      "line_type" => lower_to_upper_bits.fetch(position - 1) == "1" ? 9 : 6,
      "text" => line.fetch("text"),
      "commentary" => line.fetch("commentary")
    }
  end

  # 乾、坤的用九/用六不属于通常的 384 爻，但仍保留在显示语料中。
  if source.fetch("yao_ci").size > 6
    lines << {
      "line_number" => 7,
      "line_type" => key == "111111" ? 9 : 6,
      "text" => source.fetch("yao_ci").fetch(6).strip,
      "commentary" => "《象》曰：#{source.fetch("xiao_xiang").fetch(6).strip}"
    }
  end

  judgment = source.fetch("gua_ci").sub(/\A#{Regexp.escape(source.fetch("name"))}[：:]\s*/, "").strip
  updated = current.merge(
    "judgment" => {
      "text" => judgment,
      "commentary" => "《彖》曰：#{source.fetch("tuan_ci").strip}"
    },
    "image" => {"text" => source.fetch("da_xiang").strip},
    "lines" => lines
  )
  [key, updated]
end

raise "all judgments must be present" unless synced.values.all? { |entry| !entry.dig("judgment", "text").to_s.empty? }
raise "all images must be present" unless synced.values.all? { |entry| !entry.dig("image", "text").to_s.empty? }
raise "expected 384 ordinary lines" unless synced.values.sum { |entry| entry.fetch("lines").count { |line| line.fetch("line_number") <= 6 } } == 384

ENGINE_TEXT_PATH.write(JSON.pretty_generate(synced) + "\n")
warn "Synchronized 64 judgments, 64 images, and 384 canonical lines into #{ENGINE_TEXT_PATH}."
