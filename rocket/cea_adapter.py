"""Optional RocketCEA adapter helpers."""
from __future__ import annotations

from typing import Optional


def isp_rocketcea(
    Pc_MPa: float,
    eps: float,
    fuel: str = "CH4",
    oxidizer: str = "LOX",
    MR: float = 3.5,
    frozen: bool = True,
) -> Optional[float]:
    """Return the RocketCEA vacuum Isp for the provided conditions.

    The helper gracefully falls back to ``None`` when RocketCEA is not
    installed or when any evaluation error occurs so callers can choose
    alternative calibration strategies.
    """

    try:
        from rocketcea.cea_obj import CEA_Obj  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        return None

    try:
        cea = CEA_Obj(oxName=oxidizer, fuelName=fuel, useFastLookup=1)
        Pc_psia = Pc_MPa * 145.038
        if frozen:
            isp = cea.Isp_PcOv_frozen(
                Pc=Pc_psia,
                MR=MR,
                eps=eps,
                frozenAtThroat=1,
                frozenAtExit=1,
            )
        else:
            isp = cea.Isp_PcOv(Pc=Pc_psia, MR=MR, eps=eps)
        return float(isp)
    except Exception:  # pragma: no cover - passthrough errors
        return None
