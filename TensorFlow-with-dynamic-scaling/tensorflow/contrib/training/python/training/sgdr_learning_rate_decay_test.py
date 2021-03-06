# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Functional test for sgdr learning rate decay."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math

from sgdr_learning_rate_decay import sgdr_decay
from tensorflow.python.platform import googletest
from tensorflow.python.framework import test_util
from tensorflow.python.framework import dtypes
from tensorflow import placeholder


class SGDRDecayTest(test_util.TensorFlowTestCase):
  """Unit tests for SGDR learning rate decay."""

  def get_original_values(self, lr, t_e, mult_factor, iter_per_epoch, epochs):
    """Get an array with learning rate values from the consecutive steps using
    the original implementation
    (https://github.com.cnpmjs.org/loshchil/SGDR/blob/master/SGDR_WRNs.py)."""
    t0 = math.pi / 2.0
    tt = 0
    te_next = t_e

    lr_values = []
    sh_lr = lr
    for epoch in range(epochs):
      for _ in range(iter_per_epoch):
        # In the original approach training function is executed here
        lr_values.append(sh_lr)
        dt = 2.0 * math.pi / float(2.0 * t_e)
        tt = tt + float(dt) / iter_per_epoch
        if tt >= math.pi:
          tt = tt - math.pi
        cur_t = t0 + tt
        new_lr = lr * (1.0 + math.sin(cur_t)) / 2.0  # lr_min = 0, lr_max = lr
        sh_lr = new_lr
      if (epoch + 1) == te_next:  # time to restart
        sh_lr = lr
        tt = 0                # by setting to 0 we set lr to lr_max, see above
        t_e = t_e * mult_factor  # change the period of restarts
        te_next = te_next + t_e  # note the next restart's epoch

    return lr_values

  def get_sgdr_values(self, lr, initial_period_steps, t_mul, iters):
    """Get an array with learning rate values from the consecutive steps
    using current tensorflow implementation."""
    with self.cached_session():
      step = placeholder(dtypes.int32)

      decay = sgdr_decay(lr, step, initial_period_steps, t_mul)
      lr_values = []
      for i in range(iters):
        lr_values.append(decay.eval(feed_dict={step: i}))

      return lr_values

  def testCompareToOriginal(self):
    """Compare values generated by tensorflow implementation to the values
    generated by the original implementation
    (https://github.com.cnpmjs.org/loshchil/SGDR/blob/master/SGDR_WRNs.py)."""
    with self.cached_session():
      lr = 10.0
      init_steps = 2
      t_mul = 3
      iters = 10
      epochs = 50

      org_lr = self.get_original_values(lr, init_steps, t_mul, iters, epochs)
      sgdr_lr = self.get_sgdr_values(lr, init_steps*iters, t_mul, iters*epochs)

      for org, sgdr in zip(org_lr, sgdr_lr):
        self.assertAllClose(org, sgdr)

  def testMDecay(self):
    """Test m_mul argument. Check values for learning rate at the beginning
    of the first, second, third and fourth period. """
    with self.cached_session():
      step = placeholder(dtypes.int32)

      lr = 0.1
      t_e = 10
      t_mul = 3
      m_mul = 0.9

      decay = sgdr_decay(lr, step, t_e, t_mul, m_mul)

      test_step = 0
      self.assertAllClose(decay.eval(feed_dict={step: test_step}),
                          lr)

      test_step = t_e
      self.assertAllClose(decay.eval(feed_dict={step: test_step}),
                          lr * m_mul)

      test_step = t_e + t_e*t_mul
      self.assertAllClose(decay.eval(feed_dict={step: test_step}),
                          lr * m_mul**2)

      test_step = t_e + t_e*t_mul + t_e * (t_mul**2)
      self.assertAllClose(decay.eval(feed_dict={step: test_step}),
                          lr * (m_mul**3))

  def testCos(self):
    """Check learning rate values at the beginning, in the middle
    and at the end of the period."""
    with self.cached_session():
      step = placeholder(dtypes.int32)
      lr = 0.2
      t_e = 1000
      t_mul = 1

      decay = sgdr_decay(lr, step, t_e, t_mul)

      test_step = 0
      self.assertAllClose(decay.eval(feed_dict={step: test_step}), lr)

      test_step = t_e//2
      self.assertAllClose(decay.eval(feed_dict={step: test_step}), lr/2)

      test_step = t_e
      self.assertAllClose(decay.eval(feed_dict={step: test_step}), lr)

      test_step = t_e*3//2
      self.assertAllClose(decay.eval(feed_dict={step: test_step}), lr/2)

if __name__ == "__main__":
  googletest.main()
