"""Pure V03 expectation sanity, not real service/registry/qualification proof."""
import copy
import unittest

from t16_assertions import (
    assert_acyclic_edges, assert_allocation_only, assert_metric,
    assert_scope, assert_unmeasured,
)


class PreparationSanity(unittest.TestCase):
    def test_original_200ms_and_nearest_rank(self):
        reference = [(f"U{i}", i * 3_000_000, i * 3_000_000 + 1_000_000)
                     for i in range(20)]
        predicted = [(key, start + (i + 1) * 10_000, end + (i + 1) * 10_000)
                     for i, (key, start, end) in enumerate(reference)]
        result = assert_metric(predicted, reference, 100_000_000, 20, 190_000)
        self.assertEqual(result["p95_error_us"], 190_000)
        self.assertEqual(assert_metric([("U", 200_000, 1_200_000)],
                                      [("U", 0, 1_000_000)], 2_000_000, 1, 200_000)["N"], 1)
        with self.assertRaises(AssertionError):
            assert_metric([("U", 200_001, 1_200_001)],
                          [("U", 0, 1_000_000)], 2_000_000, 1, 200_001)

    def test_ten_unit_one_bad_endpoint_separates_2N(self):
        references = [(f"U{i}", i * 3_000_000, i * 3_000_000 + 1_000_000)
                      for i in range(10)]
        predictions = list(references)
        key, start, end = predictions[-1]
        predictions[-1] = (key, start, end + 300_000)
        # Wrong endpoint aggregation yields N=20/P95=0; original max/N rejects.
        with self.assertRaises(AssertionError):
            assert_metric(predictions, references, 100_000_000, 20, 0)
        # The correct N=10/P95=300000 also fails the unchanged 200ms release limit.
        with self.assertRaises(AssertionError):
            assert_metric(predictions, references, 100_000_000, 10, 300_000)

    def test_all_units_unique_complete_and_bounded(self):
        reference = [("U0", 0, 1_000_000), ("U1", 2_000_000, 3_000_000)]
        variants = [
            [reference[0], reference[0]],
            [reference[0]],
            [reference[0], ("UX", 2_000_000, 3_000_000)],
            [("U0", False, 1_000_000), reference[1]],
            [("U0", -1, 1_000_000), reference[1]],
            [reference[0], ("U1", 2_000_000, 10_000_001)],
            [],
        ]
        for predicted in variants:
            with self.subTest(predicted=predicted), self.assertRaises(AssertionError):
                assert_metric(predicted, reference, 10_000_000, 2, 0)
        self.assertEqual(assert_metric(reference[::-1], reference,
                                      10_000_000, 2, 0)["N"], 2)

    def test_three_scopes_never_substitute(self):
        scopes = ("capability_benchmark", "work_runtime_validation",
                  "per_work_reference_measurement")
        for actual in scopes:
            assert_scope(actual, actual)
            for required in scopes:
                if actual != required:
                    with self.subTest(actual=actual, required=required), self.assertRaises(AssertionError):
                        assert_scope(actual, required)

    def test_absent_reference_has_all_nulls_and_no_measurement_file(self):
        assessment = {"evaluation_scope": "per_work_reference_measurement",
                      "status": "not_measured", "sample_count": None, "p95_error_us": None,
                      "reference_ref": None, "measurement_report_locator": None}
        assert_unmeasured(assessment, [])
        for field in ("sample_count", "p95_error_us", "reference_ref", "measurement_report_locator"):
            changed = copy.deepcopy(assessment)
            changed[field] = 0
            with self.subTest(field=field), self.assertRaises(AssertionError):
                assert_unmeasured(changed, [])
        with self.assertRaises(AssertionError):
            assert_unmeasured(assessment, ["fake-empty-report"])

    def test_allocation_and_finished_dependencies_are_distinct(self):
        allocation = {"preparation_id": "P", "artifact_id": "A", "material_id": "M"}
        assert_allocation_only(allocation)
        for field in ("sha256", "size", "decoded", "validated"):
            with self.subTest(field=field), self.assertRaises(AssertionError):
                assert_allocation_only(allocation | {field: "future"})
        edges = [("Alignment", []), ("Measurement", ["Alignment"]),
                 ("WorkValidation", ["Alignment", "Measurement"]),
                 ("Quality", ["WorkValidation"]), ("Manifest", ["Quality", "Measurement"])]
        self.assertEqual(len(assert_acyclic_edges(edges)), 5)
        with self.assertRaises(AssertionError):
            assert_acyclic_edges([("Alignment", ["Measurement"]), ("Measurement", ["Alignment"])])
        with self.assertRaises(AssertionError):
            assert_acyclic_edges([("Manifest", ["missing-report"])])


if __name__ == "__main__":
    unittest.main()
