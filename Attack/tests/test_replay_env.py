"""Unit test for OfflineAttackEnv to verify fidelity with Phase A ground truth."""

import unittest
import numpy as np
from replay_env import OfflineAttackEnv, ATTACK_KEYS_22


class TestOfflineAttackEnv(unittest.TestCase):

    def setUp(self):
        self.env = OfflineAttackEnv(base_dir="e:/Attack/Attack", max_budget_k=5)

    def test_dataset_size_and_baseline_counts(self):
        self.assertEqual(len(self.env.claims), 1120, "Dataset must have exactly 1,120 claims")
        self.assertEqual(int(np.sum(self.env.is_baseline_failure)), 288, "Must have exactly 288 baseline failures")
        self.assertEqual(len(self.env.valid_claim_ids), 832, "Must have exactly 832 valid baseline claims")

    def test_state_dimensions(self):
        state = self.env.reset(claim_id=0)
        self.assertEqual(state.shape, (859,), "State vector must be exactly 859-dimensional")

    def test_step_budget_k(self):
        self.env.reset(claim_id=0)
        done = False
        steps = 0
        while not done:
            state, reward, done, info = self.env.step(action=steps)
            steps += 1
        self.assertEqual(steps, 5, "Episode must terminate after K=5 steps")
        self.assertTrue(done)

    def test_no_duplicate_action_allowed(self):
        self.env.reset(claim_id=0)
        _, r1, done1, info1 = self.env.step(action=0)
        _, r2, done2, info2 = self.env.step(action=0)
        self.assertTrue(info2.get("repeated", False), "Repeating an action must be flagged as repeated")
        self.assertLess(r2, 0, "Repeated action must receive a negative penalty")


if __name__ == "__main__":
    unittest.main()
