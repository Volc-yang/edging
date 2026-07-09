#!/usr/bin/env ruby
# frozen_string_literal: true

require "json"
require "pathname"
require "time"
require "yaml"

class DeterministicScorer
  SUBJECT_TYPES = %w[self pair non_human_object].freeze
  MODES = %w[questionnaire free_text hybrid].freeze

  def initialize(root:)
    @root = Pathname(root)
    @feature_schema = load_yaml("docs/02-domain-model/feature-schema.v0.1.yaml")
    @families_data = load_yaml("docs/02-domain-model/hexagram-families.v0.1.yaml")
    @prototypes_data = load_yaml("docs/02-domain-model/line-prototypes.seed.yaml")
    @transition_rules_data = load_yaml("docs/02-domain-model/transition-rules.seed.yaml")

    @dimensions = @feature_schema.fetch("dimensions").map { |dimension| dimension.fetch("key") }
    @families = @families_data.fetch("families")
    @prototypes = @prototypes_data.fetch("prototypes")
    @family_by_id = @families.to_h { |family| [family.fetch("id"), family] }
    @prototypes_by_family = @prototypes.group_by { |prototype| prototype.fetch("family_id") }
    @family_centroids = build_family_centroids
  end

  def score(observation_input)
    validation = validate_input(observation_input)
    if validation["status"] == "rejected"
      return {
        "score_result" => {
          "validation_status" => validation["status"],
          "validation" => validation,
          "top_families" => [],
          "top_prototypes" => [],
          "family_distribution" => {},
          "prototype_distribution" => {},
          "uncertainty" => rejected_uncertainty(validation),
          "probe_target" => nil,
          "explanation_basis" => explanation_basis(validation["applied_dimensions"], [])
        }
      }
    end

    applied_dimensions = validation["applied_dimensions"]
    weights = equal_weights(applied_dimensions)
    prototype_scores = build_prototype_scores(observation_input.fetch("feature_vector"), applied_dimensions, weights)
    family_scores = build_family_scores(prototype_scores)
    family_distribution = normalize_family_scores(family_scores)
    uncertainty = build_uncertainty(validation, family_distribution, prototype_scores)
    probe_target = build_probe_target(validation, family_distribution, prototype_scores)

    {
      "score_result" => {
        "validation_status" => validation["status"],
        "validation" => validation,
        "top_families" => ranked_family_entries(family_distribution, family_scores).first(3),
        "top_prototypes" => ranked_prototype_entries(prototype_scores).first(5),
        "edge_vector" => {
          "basis" => "hexagram_family",
          "values" => family_distribution
        },
        "family_distribution" => family_distribution,
        "prototype_distribution" => prototype_scores.each_with_object({}) do |entry, distribution|
          distribution[entry.fetch("prototype_id")] = round(entry.fetch("score"))
        end,
        "uncertainty" => uncertainty,
        "probe_target" => probe_target,
        "explanation_basis" => explanation_basis(applied_dimensions, [])
      }
    }
  end

  private

  def load_yaml(relative_path)
    YAML.load_file(@root.join(relative_path))
  end

  def validate_input(observation_input)
    feature_vector = observation_input["feature_vector"] || {}
    missing_dimensions = @dimensions.reject { |dimension| feature_vector.key?(dimension) }
    out_of_range_dimensions = feature_vector.each_with_object([]) do |(dimension, value), out_of_range|
      next unless @dimensions.include?(dimension)
      out_of_range << dimension unless value.is_a?(Numeric) && value >= 0.0 && value <= 1.0
    end
    unknown_dimensions = feature_vector.keys - @dimensions

    policy_flags = []
    policy_flags << "unsupported_subject_type" unless SUBJECT_TYPES.include?(observation_input["subject_type"])
    policy_flags << "unsupported_mode" unless MODES.include?(observation_input["mode"])
    policy_flags << "missing_timestamp" if observation_input["timestamp"].to_s.strip.empty?
    policy_flags << "unknown_dimensions_present" unless unknown_dimensions.empty?

    applied_dimensions = @dimensions - missing_dimensions - out_of_range_dimensions

    status =
      if !policy_flags.empty? || applied_dimensions.empty?
        "rejected"
      elsif missing_dimensions.empty?
        "valid"
      else
        "partially_valid"
      end

    {
      "status" => status,
      "missing_dimensions" => missing_dimensions,
      "out_of_range_dimensions" => out_of_range_dimensions,
      "unknown_dimensions" => unknown_dimensions,
      "policy_flags" => policy_flags,
      "applied_dimensions" => applied_dimensions
    }
  end

  def equal_weights(dimensions)
    return {} if dimensions.empty?

    weight = 1.0 / dimensions.length
    dimensions.each_with_object({}) { |dimension, memo| memo[dimension] = weight }
  end

  def build_prototype_scores(feature_vector, applied_dimensions, weights)
    @prototypes.map do |prototype|
      match_score = feature_match(feature_vector, prototype.fetch("feature_vector"), applied_dimensions, weights)
      rule_adjustment = 0.0
      {
        "prototype_id" => prototype.fetch("id"),
        "family_id" => prototype.fetch("family_id"),
        "line_index" => prototype.fetch("line_index"),
        "state_name" => prototype.fetch("state_name"),
        "score" => clip(match_score + rule_adjustment)
      }
    end
  end

  def feature_match(feature_vector, prototype_vector, applied_dimensions, weights)
    distance = applied_dimensions.sum do |dimension|
      weights.fetch(dimension) * (feature_vector.fetch(dimension) - prototype_vector.fetch(dimension)).abs
    end
    clip(1.0 - distance)
  end

  def build_family_scores(prototype_scores)
    grouped_scores = prototype_scores.group_by { |entry| entry.fetch("family_id") }

    @families.map do |family|
      family_id = family.fetch("id")
      scores = grouped_scores.fetch(family_id).sort_by { |entry| entry.fetch("line_index") }
      max_score = scores.map { |entry| entry.fetch("score") }.max || 0.0
      mean_score = scores.sum { |entry| entry.fetch("score") } / scores.length
      coherence = local_coherence(scores)
      raw_score = 0.60 * max_score + 0.25 * mean_score + 0.15 * coherence

      {
        "family_id" => family_id,
        "raw_score" => raw_score,
        "max_prototype_score" => max_score,
        "mean_prototype_score" => mean_score,
        "local_coherence" => coherence
      }
    end
  end

  def local_coherence(scores)
    adjacent_averages = scores.each_cons(2).map do |left, right|
      (left.fetch("score") + right.fetch("score")) / 2.0
    end
    adjacent_averages.max || 0.0
  end

  def normalize_family_scores(family_scores)
    total = family_scores.sum { |entry| entry.fetch("raw_score") }
    return family_scores.each_with_object({}) { |entry, memo| memo[entry.fetch("family_id")] = 0.0 } if total <= 0.0

    family_scores.each_with_object({}) do |entry, normalized|
      normalized[entry.fetch("family_id")] = round(entry.fetch("raw_score") / total)
    end
  end

  def build_uncertainty(validation, family_distribution, prototype_scores)
    family_ranking = family_distribution.sort_by { |_family_id, score| -score }
    prototype_ranking = prototype_scores.sort_by { |entry| -entry.fetch("score") }

    top_family_gap = gap_between_top_two(family_ranking.map(&:last))
    top_prototype_gap = gap_between_top_two(prototype_ranking.map { |entry| entry.fetch("score") })
    h_proxy = 1.0 - (family_ranking.first&.last || 0.0)
    prototype_conflict_flag = prototype_conflict?(prototype_ranking.first(2))
    missing_ratio = validation.fetch("missing_dimensions").length.to_f / @dimensions.length

    overall =
      0.30 * missing_ratio +
      0.25 * (1.0 - top_family_gap) +
      0.20 * (1.0 - top_prototype_gap) +
      0.15 * h_proxy +
      0.10 * (prototype_conflict_flag ? 1.0 : 0.0)

    {
      "overall" => round(clip(overall)),
      "top_family_gap" => round(top_family_gap),
      "top_prototype_gap" => round(top_prototype_gap),
      "family_entropy_proxy" => round(h_proxy),
      "missing_dimensions" => validation.fetch("missing_dimensions"),
      "prototype_conflict_flag" => prototype_conflict_flag
    }
  end

  def build_probe_target(validation, family_distribution, prototype_scores)
    missing_dimensions = validation.fetch("missing_dimensions")
    unless missing_dimensions.empty?
      dimension = missing_dimensions.first
      return {
        "dimension" => dimension,
        "reason" => "input is incomplete and this dimension is missing from the observation"
      }
    end

    family_ranking = family_distribution.sort_by { |_family_id, score| -score }
    if family_ranking.length >= 2
      top_family_id = family_ranking[0].first
      next_family_id = family_ranking[1].first
      dimension = most_separating_dimension(@family_centroids.fetch(top_family_id), @family_centroids.fetch(next_family_id))
      return {
        "dimension" => dimension,
        "reason" => "top family candidates #{top_family_id} and #{next_family_id} differ most on this dimension"
      }
    end

    top_prototypes = prototype_scores.sort_by { |entry| -entry.fetch("score") }.first(2)
    return nil if top_prototypes.length < 2

    left = prototype_feature_vector(top_prototypes[0].fetch("prototype_id"))
    right = prototype_feature_vector(top_prototypes[1].fetch("prototype_id"))
    dimension = most_separating_dimension(left, right)

    {
      "dimension" => dimension,
      "reason" => "top prototype candidates differ most on this dimension"
    }
  end

  def ranked_family_entries(family_distribution, family_scores)
    by_family_id = family_scores.to_h { |entry| [entry.fetch("family_id"), entry] }

    family_distribution
      .sort_by { |family_id, score| [-score, @family_by_id.fetch(family_id).fetch("index")] }
      .map do |family_id, score|
        family = @family_by_id.fetch(family_id)
        raw_metrics = by_family_id.fetch(family_id)
        {
          "family_id" => family_id,
          "index" => family.fetch("index"),
          "name_cn" => family.fetch("name_cn"),
          "name_en" => family.fetch("name_en"),
          "score" => round(score),
          "raw_score" => round(raw_metrics.fetch("raw_score")),
          "max_prototype_score" => round(raw_metrics.fetch("max_prototype_score")),
          "local_coherence" => round(raw_metrics.fetch("local_coherence"))
        }
      end
  end

  def ranked_prototype_entries(prototype_scores)
    prototype_scores
      .sort_by { |entry| [-entry.fetch("score"), entry.fetch("prototype_id")] }
      .map do |entry|
        {
          "prototype_id" => entry.fetch("prototype_id"),
          "family_id" => entry.fetch("family_id"),
          "line_index" => entry.fetch("line_index"),
          "state_name" => entry.fetch("state_name"),
          "score" => round(entry.fetch("score"))
        }
      end
  end

  def build_family_centroids
    @prototypes_by_family.each_with_object({}) do |(family_id, prototypes), centroids|
      centroid = @dimensions.each_with_object({}) do |dimension, memo|
        memo[dimension] = prototypes.sum { |prototype| prototype.fetch("feature_vector").fetch(dimension) } / prototypes.length
      end
      centroids[family_id] = centroid
    end
  end

  def most_separating_dimension(left_vector, right_vector)
    @dimensions.max_by do |dimension|
      (left_vector.fetch(dimension) - right_vector.fetch(dimension)).abs
    end
  end

  def prototype_feature_vector(prototype_id)
    prototype = @prototypes.find { |entry| entry.fetch("id") == prototype_id }
    prototype.fetch("feature_vector")
  end

  def prototype_conflict?(top_two_prototypes)
    return false if top_two_prototypes.length < 2

    left = top_two_prototypes[0]
    right = top_two_prototypes[1]
    close_gap = (left.fetch("score") - right.fetch("score")).abs < 0.08

    if left.fetch("family_id") == right.fetch("family_id")
      close_gap && (left.fetch("line_index") - right.fetch("line_index")).abs >= 2
    else
      close_gap
    end
  end

  def gap_between_top_two(values)
    return 0.0 if values.empty?
    return round(values.first) if values.length == 1

    round(values[0] - values[1])
  end

  def explanation_basis(applied_dimensions, rule_adjustments_applied)
    {
      "scoring_version" => "0.1",
      "feature_schema_version" => @feature_schema.fetch("version"),
      "family_registry_version" => @families_data.fetch("version"),
      "prototype_registry_version" => @prototypes_data.fetch("version"),
      "transition_rules_version" => @transition_rules_data.fetch("version"),
      "dimension_weights" => applied_dimensions.each_with_object({}) do |dimension, memo|
        memo[dimension] = round(1.0 / applied_dimensions.length)
      end,
      "rule_adjustments_applied" => rule_adjustments_applied
    }
  end

  def rejected_uncertainty(validation)
    {
      "overall" => 1.0,
      "top_family_gap" => 0.0,
      "top_prototype_gap" => 0.0,
      "family_entropy_proxy" => 1.0,
      "missing_dimensions" => validation.fetch("missing_dimensions"),
      "prototype_conflict_flag" => false
    }
  end

  def clip(value, lower = 0.0, upper = 1.0)
    [[value, lower].max, upper].min
  end

  def round(value)
    value.round(6)
  end
end

if $PROGRAM_NAME == __FILE__
  root = Pathname(__dir__).join("..").expand_path
  input_path = ARGV[0] || root.join("examples/sample-observation.v0.1.yaml")
  observation = YAML.load_file(input_path)
  observation_input = observation.fetch("observation_input")
  result = DeterministicScorer.new(root: root).score(observation_input)
  puts JSON.pretty_generate(result)
end
