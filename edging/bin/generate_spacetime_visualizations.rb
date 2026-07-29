#!/usr/bin/env ruby
# frozen_string_literal: true

require "cgi"
require "fileutils"
require "pathname"
require "yaml"

ROOT = Pathname(__dir__).join("..").expand_path
DOMAIN_DIR = ROOT.join("docs/02-domain-model")
OUTPUT_DIR = DOMAIN_DIR.join("visualizations")

PHASE_COLORS = {
  "shaoyang" => "#31A36F",
  "taiyang" => "#E8A229",
  "shaoyin" => "#4A82C3",
  "taiyin" => "#7857A6"
}.freeze

PHASE_LABELS = {
  "shaoyang" => "少阳 · 生发",
  "taiyang" => "太阳 · 鼎盛",
  "shaoyin" => "少阴 · 收敛",
  "taiyin" => "太阴 · 寂藏"
}.freeze

LINE_COLORS = {
  1 => "#D84A3A",
  2 => "#E68A2E",
  3 => "#C4A72E",
  4 => "#2F9C73",
  5 => "#377FB5",
  6 => "#7654A8"
}.freeze

def load_yaml(path)
  YAML.safe_load(path.read, aliases: true)
end

def esc(value)
  CGI.escapeHTML(value.to_s)
end

def polar(cx, cy, radius, degrees)
  radians = degrees * Math::PI / 180.0
  [cx + radius * Math.cos(radians), cy + radius * Math.sin(radians)]
end

def arc_path(cx, cy, radius, start_degrees, end_degrees)
  start_point = polar(cx, cy, radius, start_degrees)
  end_point = polar(cx, cy, radius, end_degrees)
  sweep = end_degrees - start_degrees > 180 ? 1 : 0
  format("M %.2f %.2f A %.2f %.2f 0 %d 1 %.2f %.2f", start_point[0], start_point[1], radius, radius, sweep, end_point[0], end_point[1])
end

def svg_document(width, height, body)
  <<~SVG
    <?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="#{width}" height="#{height}" viewBox="0 0 #{width} #{height}">
      <rect width="100%" height="100%" fill="#F7F8F6"/>
      <style>
        text { font-family: "PingFang SC", "Noto Sans CJK SC", sans-serif; fill: #19211D; }
        .title { font-size: 30px; font-weight: 700; }
        .subtitle { font-size: 14px; fill: #53605A; }
        .section { font-size: 18px; font-weight: 700; }
        .cell-name { font-size: 17px; font-weight: 700; }
        .cell-meta { font-size: 10px; fill: #53605A; }
        .circle-name { font-size: 10px; font-weight: 600; }
        .legend { font-size: 12px; fill: #38443E; }
      </style>
      #{body}
    </svg>
  SVG
end

hexagrams = load_yaml(DOMAIN_DIR.join("hexagram-spacetime.v0.1.yaml")).fetch("hexagrams")
lines = load_yaml(DOMAIN_DIR.join("line-structures.v0.1.yaml")).fetch("lines")
confirmed = load_yaml(DOMAIN_DIR.join("confirmed-line-abstractions.v0.1.yaml")).fetch("abstractions")
drafts = load_yaml(DOMAIN_DIR.join("draft-line-abstractions.v0.1.yaml")).fetch("abstractions")
confirmed_counts = confirmed.group_by { |entry| entry.fetch("id").match(/proto_hex_(\d+)_/)[1].to_i }.transform_values(&:size)
draft_counts = drafts.group_by { |entry| entry.fetch("id").match(/proto_hex_(\d+)_/)[1].to_i }.transform_values(&:size)

FileUtils.mkdir_p(OUTPUT_DIR)

# Combined square-space and circle-time map.
parts = []
parts << '<text x="48" y="50" class="title">先天六十四卦 · 方圆时空抽象</text>'
parts << '<text x="48" y="78" class="subtitle">方图定位空间组合，圆图定位时间相位；颜色来自复为时间原点的四象分段</text>'
parts << '<text x="48" y="116" class="section">方图 · 空间序列</text>'
parts << '<text x="760" y="116" class="section">圆图 · 时间序列</text>'

square_x = 48
square_y = 142
cell = 72

hexagrams.each do |hexagram|
  row = hexagram.dig("square", "row_top_to_bottom") - 1
  column = hexagram.dig("square", "column_left_to_right") - 1
  x = square_x + column * cell
  y = square_y + row * cell
  phase = hexagram.dig("circle_time", "phase")
  color = PHASE_COLORS.fetch(phase)
  count = confirmed_counts.fetch(hexagram.fetch("king_wen_index"), 0)
  draft_count = draft_counts.fetch(hexagram.fetch("king_wen_index"), 0)
  coordinate = hexagram.dig("square", "coordinate_upper_lower")
  parts << %(<rect x="#{x}" y="#{y}" width="#{cell}" height="#{cell}" fill="#{color}" fill-opacity="0.13" stroke="#9CA7A1" stroke-width="0.8"/>)
  parts << %(<rect x="#{x + 1.5}" y="#{y + 1.5}" width="#{cell - 3}" height="4" fill="#{color}"/>)
  parts << %(<text x="#{x + cell / 2}" y="#{y + 31}" text-anchor="middle" class="cell-name">#{esc(hexagram.fetch("name_cn"))}</text>)
  parts << %(<text x="#{x + cell / 2}" y="#{y + 48}" text-anchor="middle" class="cell-meta">#{coordinate[0]},#{coordinate[1]} · t#{hexagram.dig("circle_time", "cycle_index_fu_origin")}</text>)
  parts << %(<text x="#{x + cell / 2}" y="#{y + 63}" text-anchor="middle" class="cell-meta">确#{count} · 草#{draft_count}</text>)
end

8.times do |index|
  number = 8 - index
  parts << %(<text x="#{square_x + index * cell + cell / 2}" y="#{square_y - 9}" text-anchor="middle" class="legend">上 #{number}</text>)
  parts << %(<text x="#{square_x - 10}" y="#{square_y + index * cell + cell / 2 + 4}" text-anchor="end" class="legend">下 #{number}</text>)
end

cx = 1045
cy = 418
node_radius = 244
label_radius = 268

PHASES = %w[shaoyang taiyang shaoyin taiyin].freeze
PHASES.each_with_index do |phase, phase_index|
  # Cycle starts at Fu (circle index 33), while the diagram angle starts at Qian.
  circle_start = (33 + phase_index * 16) % 64
  start_angle = -90 + circle_start * 360.0 / 64 - 2.5
  end_angle = start_angle + 15 * 360.0 / 64 + 5
  parts << %(<path d="#{arc_path(cx, cy, 218, start_angle, end_angle)}" fill="none" stroke="#{PHASE_COLORS.fetch(phase)}" stroke-width="14" stroke-linecap="round" opacity="0.26"/>)
end

hexagrams.sort_by { |entry| entry.dig("circle_time", "circle_index_qian_origin_clockwise") }.each do |hexagram|
  index = hexagram.dig("circle_time", "circle_index_qian_origin_clockwise")
  angle = -90 + index * 360.0 / 64
  node = polar(cx, cy, node_radius, angle)
  label = polar(cx, cy, label_radius, angle)
  phase = hexagram.dig("circle_time", "phase")
  color = PHASE_COLORS.fetch(phase)
  count = confirmed_counts.fetch(hexagram.fetch("king_wen_index"), 0)
  draft_count = draft_counts.fetch(hexagram.fetch("king_wen_index"), 0)
  normalized = (angle % 360 + 360) % 360
  right_side = normalized <= 90 || normalized >= 270
  rotation = right_side ? angle : angle + 180
  anchor = right_side ? "start" : "end"
  if draft_count.positive?
    parts << %(<circle cx="#{node[0].round(2)}" cy="#{node[1].round(2)}" r="7" fill="none" stroke="#53605A" stroke-width="1.2" stroke-dasharray="2 1.5"/>)
  end
  parts << %(<circle cx="#{node[0].round(2)}" cy="#{node[1].round(2)}" r="#{count.positive? ? 5.0 : 3.4}" fill="#{color}" stroke="#{count.positive? ? '#19211D' : '#FFFFFF'}" stroke-width="#{count.positive? ? 1.2 : 0.8}"/>)
  parts << %(<text x="#{label[0].round(2)}" y="#{label[1].round(2)}" text-anchor="#{anchor}" dominant-baseline="middle" transform="rotate(#{rotation.round(2)} #{label[0].round(2)} #{label[1].round(2)})" class="circle-name">#{esc(hexagram.fetch("name_cn"))}</text>)
end

parts << %(<text x="#{cx}" y="#{cy - 18}" text-anchor="middle" class="section">圆图时间</text>)
parts << %(<text x="#{cx}" y="#{cy + 8}" text-anchor="middle" class="subtitle">复 t0 · 乾 t31</text>)
parts << %(<text x="#{cx}" y="#{cy + 30}" text-anchor="middle" class="subtitle">姤 t32 · 坤 t63</text>)

legend_y = 750
PHASES.each_with_index do |phase, index|
  x = 54 + index * 185
  parts << %(<rect x="#{x}" y="#{legend_y}" width="16" height="16" rx="3" fill="#{PHASE_COLORS.fetch(phase)}"/>)
  parts << %(<text x="#{x + 24}" y="#{legend_y + 13}" class="legend">#{PHASE_LABELS.fetch(phase)}</text>)
end
parts << %(<circle cx="830" cy="#{legend_y + 8}" r="5" fill="#FFFFFF" stroke="#19211D" stroke-width="1.2"/>)
parts << %(<text x="844" y="#{legend_y + 13}" class="legend">已有确认爻</text>)
parts << %(<circle cx="980" cy="#{legend_y + 8}" r="7" fill="none" stroke="#53605A" stroke-width="1.2" stroke-dasharray="2 1.5"/>)
parts << %(<text x="994" y="#{legend_y + 13}" class="legend">含待审草案</text>)
parts << %(<text x="48" y="790" class="subtitle">注：方图相邻和圆图相邻都不自动等于单爻变；单爻变只由六位向量翻转一个分量定义。</text>)

OUTPUT_DIR.join("hexagram-square-circle-map.svg").write(svg_document(1400, 820, parts.join("\n")))

# Six panels showing the 384 directed changes as 192 bidirectional pairs.
parts = []
parts << '<defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>'
parts << '<text x="44" y="50" class="title">384爻 · 六层单爻变换图</text>'
parts << '<text x="44" y="78" class="subtitle">每层64个起点、32对可逆连接；初二三改变下卦轴，四五上改变上卦轴</text>'

panel_w = 380
panel_h = 370
grid_cell = 34
grid_size = grid_cell * 8

(1..6).each do |line_index|
  panel_column = (line_index - 1) % 3
  panel_row = (line_index - 1) / 3
  px = 44 + panel_column * 410
  py = 108 + panel_row * 390
  gx = px + 52
  gy = py + 54
  color = LINE_COLORS.fetch(line_index)
  level_name = %w[初爻 二爻 三爻 四爻 五爻 上爻].fetch(line_index - 1)
  axis_name = line_index <= 3 ? "下卦轴" : "上卦轴"
  weight = [4, 2, 1].fetch((line_index - 1) % 3)

  parts << %(<rect x="#{px}" y="#{py}" width="#{panel_w}" height="#{panel_h}" rx="6" fill="#FFFFFF" stroke="#D4DAD6"/>)
  parts << %(<text x="#{px + 18}" y="#{py + 28}" class="section" fill="#{color}">#{level_name}</text>)
  parts << %(<text x="#{px + 100}" y="#{py + 27}" class="subtitle">#{axis_name} · 步长 #{weight}</text>)

  panel_lines = lines.select { |entry| entry.fetch("line_index") == line_index }
  seen_pairs = {}
  panel_lines.each do |entry|
    source = entry.dig("fixed", "spatial_coordinate_upper_lower_line")[0, 2]
    target = entry.dig("change", "target_coordinate_upper_lower")
    pair_key = [source, target].sort
    next if seen_pairs[pair_key]

    seen_pairs[pair_key] = true
    sx = gx + (9 - source[0] - 0.5) * grid_cell
    sy = gy + (9 - source[1] - 0.5) * grid_cell
    tx = gx + (9 - target[0] - 0.5) * grid_cell
    ty = gy + (9 - target[1] - 0.5) * grid_cell
    parts << %(<line x1="#{sx}" y1="#{sy}" x2="#{tx}" y2="#{ty}" stroke="#{color}" stroke-width="1.6" opacity="0.55" marker-start="url(#arrow)" marker-end="url(#arrow)"/>)
  end

  8.times do |row|
    8.times do |column|
      x = gx + column * grid_cell
      y = gy + row * grid_cell
      parts << %(<rect x="#{x}" y="#{y}" width="#{grid_cell}" height="#{grid_cell}" fill="none" stroke="#E3E7E4" stroke-width="0.6"/>)
      parts << %(<circle cx="#{x + grid_cell / 2}" cy="#{y + grid_cell / 2}" r="2.4" fill="#28342E"/>)
    end
  end
  parts << %(<text x="#{px + 18}" y="#{py + 350}" class="legend">64条有向变化 = 32对双向连接</text>)
end

parts << '<text x="44" y="888" class="subtitle">空间步长来自先天数权重4、2、1；箭头只表示阴阳翻转可逆，不表示现实过程必然逆转。</text>'
OUTPUT_DIR.join("line-change-six-layer-map.svg").write(svg_document(1280, 920, parts.join("\n")))

warn "Generated 2 SVG visualizations in #{OUTPUT_DIR}."
