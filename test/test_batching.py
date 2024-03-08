import scipy
import numpy as np
import jax
from jax.test_util import check_grads
import jax_linop

import pytest
pmp = pytest.mark.parametrize

jax.config.update("jax_enable_x64", True)


def f(out, args, kwargs_dump):
    x, y = args
    kwargs = jax_linop.load_kwargs(kwargs_dump)
    workers = kwargs.pop("workers", None)
    batch_axes = kwargs.pop("batch_axes", None)
    axes0 = list(range(len(x.shape)))
    axes1 = list(range(len(x.shape)))
    if batch_axes:
        axes0 = [i for i in range(len(x.shape)) if not i in batch_axes[0]]
        axes1 = [i for i in range(len(y.shape)) if not i in batch_axes[1]]
    out[0][()] = scipy.fft.fftn(x, axes=axes0, norm="forward", workers=workers)
    out[1][()] = scipy.fft.fftn(y, axes=axes1, norm="forward", workers=workers)


def f_T(out, args, kwargs_dump):
    x, y = args
    kwargs = jax_linop.load_kwargs(kwargs_dump)
    workers = kwargs.pop("workers", None)
    batch_axes = kwargs.pop("batch_axes", None)
    axes0 = list(range(len(x.shape)))
    axes1 = list(range(len(x.shape)))
    if batch_axes:
        axes0 = [i for i in range(len(x.shape)) if not i in batch_axes[0]]
        axes1 = [i for i in range(len(y.shape)) if not i in batch_axes[1]]
    out[0][()] = scipy.fft.ifftn(
        x.conj(), axes=axes0, norm="backward", workers=workers
    ).conj()
    out[1][()] = scipy.fft.ifftn(
        y.conj(), axes=axes1, norm="backward", workers=workers
    ).conj()


def f_a(*args, **kwargs):
    # Returns `shape` and `dtype` of output as well as the added batch_axes of the `output``
    batch_axes = kwargs.pop("batch_axes", None)
    x, y = args
    out_ax = [(), ()]
    if batch_axes:
        if len(batch_axes[0]) > 0 and len(batch_axes[1]) > 0:
            ia0 = batch_axes[0][-1]
            ia1 = batch_axes[1][-1]
            out_ax[0] = ia0
            out_ax[1] = ia1
        else:
            raise RuntimeError("Batching along only 1 input axis not implemented.")
    return ((x.shape, x.dtype, out_ax[0]), (y.shape, y.dtype, out_ax[1]))


def f_a_T(*args, **kwargs):
    # Returns `shape` and `dtype` of output as well as the added batch_axes of the `output``
    batch_axes = kwargs.pop("batch_axes", None)
    a, b = args
    out_ax = [(), ()]
    if batch_axes:
        if len(batch_axes[0]) > 0 and len(batch_axes[1]) > 0:
            ia0 = batch_axes[0][-1]
            ia1 = batch_axes[1][-1]
            out_ax[0] = ia0
            out_ax[1] = ia1
        else:
            raise RuntimeError("Batching along only 1 input axis not implemented.")
    return ((a.shape, a.dtype, out_ax[0]), (b.shape, b.dtype, out_ax[1]))


f_jax = jax_linop.get_linear_call(f, f_T, f_a, f_a_T, func_can_batch=False)
f_jax_can_batch = jax_linop.get_linear_call(f, f_T, f_a, f_a_T, func_can_batch=True)


rng = np.random.default_rng(42)
a1 = rng.random((5, 5, 5)) - 0.5 + 1j * (rng.random((5, 5, 5)) - 0.5)
a2 = rng.random((5, 5, 5)) - 0.5 + 1j * (rng.random((5, 5, 5)) - 0.5)
a = (a1, a2)
av1 = rng.random((5, 5, 5, 5)) - 0.5 + 1j * (rng.random((5, 5, 5, 5)) - 0.5)
av2 = rng.random((5, 5, 5, 5)) - 0.5 + 1j * (rng.random((5, 5, 5, 5)) - 0.5)
av = (av1, av2)

@pmp("bt_a1", (0,1,2))
@pmp("bt_a2", (0,1,2))
@pmp("bt2_a1", (0,1,2))
@pmp("bt2_a2", (0,1,2))
def test_vmap(bt_a1, bt_a2, bt2_a1, bt2_a2):
    vj = jax.vmap(f_jax, in_axes=(bt_a1, bt_a2))
    vb = jax.vmap(f_jax_can_batch, in_axes=(bt_a1, bt_a2))
    rj = vj(*a)
    rb = vb(*a)
    np.testing.assert_allclose(rj, rb)
    # check_grads(vj, a, order=2, modes=["fwd", "rev"], eps=1.0)
    # check_grads(vb, a, order=2, modes=["fwd", "rev"], eps=1.0)


    vvj = jax.vmap(vj, in_axes=(bt2_a1, bt2_a2))
    vvb = jax.vmap(vb, in_axes=(bt2_a1, bt2_a2))
    rb = vvb(*av)
    rj = vvj(*av)
    np.testing.assert_allclose(rj, rb)
    # check_grads(vvj, av, order=2, modes=["fwd", "rev"], eps=1.0)
    # check_grads(vvb, av, order=2, modes=["fwd", "rev"], eps=1.0)
