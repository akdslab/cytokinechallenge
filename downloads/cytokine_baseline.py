#!/usr/bin/env python3
"""An illustrative cytokine-combination benchmark. Python 3.9+, no packages.

The generated observations are synthetic numbers, not biological measurements.
The CSV schema, split and metric are teaching conventions, not release metadata
or official challenge scoring. No cell is paired with a counterfactual cell.

Run: python3 cytokine_baseline.py --output-dir demo-output
"""

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean


def canonical_condition(cytokines):
    """Treat a combination as a set: A+B and B+A are the same condition."""
    if isinstance(cytokines, str):
        raise ValueError("Pass cytokines as a list/tuple, not a joined string.")
    values = tuple(cytokines)
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Each cytokine needs a nonempty string label.")
    return tuple(sorted(set(value.strip() for value in values)))


def validate_rows(rows):
    """Validate this tutorial's in-memory schema, including feature alignment."""
    if not rows:
        raise ValueError("No observations were supplied.")
    genes = tuple(sorted(rows[0]["expression"]))
    if not genes:
        raise ValueError("At least one expression feature is required.")
    seen_ids = set()
    for row in rows:
        if not row["cell_id"] or row["cell_id"] in seen_ids:
            raise ValueError("cell_id must be nonempty and unique.")
        seen_ids.add(row["cell_id"])
        if not row["donor"]:
            raise ValueError("Every observation must have a donor label.")
        canonical_condition(row["cytokines"])
        if tuple(sorted(row["expression"])) != genes:
            raise ValueError("Every observation must have the same gene features.")
        if any(not math.isfinite(float(row["expression"][g])) for g in genes):
            raise ValueError("Expression values must be finite numbers.")
    return genes


def split_by_condition(rows, held_out):
    """Hold out whole combinations across every donor; never split their cells."""
    validate_rows(rows)
    held_out = {canonical_condition(condition) for condition in held_out}
    if not held_out or any(len(condition) < 2 for condition in held_out):
        raise ValueError("This example holds out combinations of at least two signals.")
    observed = {canonical_condition(row["cytokines"]) for row in rows}
    missing = held_out - observed
    if missing:
        raise ValueError("Requested held-out combinations are absent: %s" % sorted(missing))
    train, test = [], []
    for row in rows:
        destination = test if canonical_condition(row["cytokines"]) in held_out else train
        destination.append(row)
    if not train or not test:
        raise ValueError("The split needs observations in both training and test sets.")
    return train, test


def mean_profiles(rows):
    """Mean expression within donor x condition; no cell-to-cell matching."""
    genes = validate_rows(rows)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["donor"], canonical_condition(row["cytokines"]))].append(row)
    return {
        key: {gene: fmean(float(row["expression"][gene]) for row in group)
              for gene in genes}
        for key, group in grouped.items()
    }


@dataclass
class AdditiveModel:
    genes: tuple
    controls: dict
    effects: dict

    def predict(self, donor, cytokines):
        condition = canonical_condition(cytokines)
        if donor not in self.controls:
            raise ValueError("No training control for donor %r." % donor)
        missing = [signal for signal in condition if (donor, signal) not in self.effects]
        if missing:
            raise ValueError("Missing training single-signal data for %s: %s" % (donor, missing))
        return {
            gene: self.controls[donor][gene] + sum(
                self.effects[(donor, signal)][gene] for signal in condition
            )
            for gene in self.genes
        }


def fit_additive(train):
    """Estimate each single-signal change relative to its donor's control."""
    genes = validate_rows(train)
    profiles = mean_profiles(train)
    controls = {donor: profile for (donor, condition), profile in profiles.items()
                if not condition}
    donors = {row["donor"] for row in train}
    if donors - controls.keys():
        raise ValueError("Each training donor needs a matched-context control.")
    effects = {
        (donor, condition[0]): {gene: profile[gene] - controls[donor][gene]
                                for gene in genes}
        for (donor, condition), profile in profiles.items() if len(condition) == 1
    }
    return AdditiveModel(genes, controls, effects)


def evaluate(model, test):
    """Macro-average RMSE over donor x condition mean expression profiles.

    This small teaching metric does not evaluate cell-state distributions,
    differential expression, or new-donor transfer. It is not official scoring.
    """
    if validate_rows(test) != model.genes:
        raise ValueError("Training and test feature names must agree.")
    results = []
    for (donor, condition), observed in sorted(mean_profiles(test).items()):
        predicted = model.predict(donor, condition)
        control = model.controls[donor]
        rmse = math.sqrt(fmean((predicted[g] - observed[g]) ** 2 for g in model.genes))
        control_rmse = math.sqrt(fmean((control[g] - observed[g]) ** 2 for g in model.genes))
        results.append({
            "donor": donor, "cytokines": list(condition),
            "rmse_additive": rmse, "rmse_control_only": control_rmse,
            "observed_mean": observed, "predicted_mean": predicted,
        })
    return {
        "metric": "mean donor-condition RMSE across all toy genes",
        "rmse_additive": fmean(item["rmse_additive"] for item in results),
        "rmse_control_only": fmean(item["rmse_control_only"] for item in results),
        "n_profiles": len(results), "profiles": results,
    }


def make_synthetic_rows(seed=7, cells_per_condition=24):
    """Invent numeric signals A/B/C and genes; encode no biological claims."""
    if cells_per_condition < 1:
        raise ValueError("cells_per_condition must be positive.")
    rng = random.Random(seed)
    genes = tuple("gene_%02d" % i for i in range(1, 7))
    changes = {
        "signal_A": (1.0, 0.7, 0.0, -0.2, 0.0, 0.3),
        "signal_B": (0.0, 0.6, 1.1, 0.2, -0.2, 0.0),
        "signal_C": (0.2, 0.0, -0.3, 0.9, 0.6, 0.1),
    }
    conditions = [(), ("signal_A",), ("signal_B",), ("signal_C",),
                  ("signal_A", "signal_B"), ("signal_A", "signal_C"),
                  ("signal_B", "signal_C")]
    rows = []
    for donor_index in range(3):
        donor = "toy_donor_%s" % (donor_index + 1)
        for condition in conditions:
            for _ in range(cells_per_condition):
                values = {}
                for gene_index, gene in enumerate(genes):
                    control = 2.0 + 0.2 * gene_index + 0.1 * donor_index
                    delta = sum(changes[signal][gene_index] for signal in condition)
                    # A deliberately invented interaction the additive model cannot fit.
                    interaction = 0.8 if condition == ("signal_A", "signal_B") and gene_index == 0 else 0.0
                    values[gene] = control + delta + interaction + rng.gauss(0.0, 0.15)
                rows.append({"cell_id": "toy_cell_%04d" % len(rows), "donor": donor,
                             "cytokines": condition, "expression": values})
    return rows


def write_outputs(directory, rows, train, report):
    """Export only generated toy data and its audit/results, never real data."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    genes = validate_rows(rows)
    train_ids = {row["cell_id"] for row in train}
    with (directory / "synthetic_cells.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cell_id", "donor", "cytokines", "split"] + list(genes))
        writer.writeheader()
        for row in rows:
            writer.writerow({"cell_id": row["cell_id"], "donor": row["donor"],
                             "cytokines": ";".join(canonical_condition(row["cytokines"])),
                             "split": "train" if row["cell_id"] in train_ids else "test",
                             **row["expression"]})
    (directory / "synthetic_metrics.json").write_text(json.dumps(report, indent=2) + "\n")


def run_demo(output_dir=None):
    rows = make_synthetic_rows()
    held_out = [("signal_A", "signal_B"), ("signal_A", "signal_C"), ("signal_B", "signal_C")]
    train, test = split_by_condition(rows, held_out)
    model = fit_additive(train)
    report = evaluate(model, test)
    summary = {"data": "synthetic teaching example; not biological measurements",
               "n_cells_train": len(train), "n_cells_test": len(test),
               "held_out_combinations": [list(item) for item in held_out],
               "rmse_additive": report["rmse_additive"],
               "rmse_control_only": report["rmse_control_only"],
               "n_profiles": report["n_profiles"]}
    print(json.dumps(summary, indent=2))
    if output_dir is not None:
        write_outputs(output_dir, rows, train, report)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Optionally write synthetic CSV and JSON results here.")
    arguments = parser.parse_args()
    run_demo(arguments.output_dir)
