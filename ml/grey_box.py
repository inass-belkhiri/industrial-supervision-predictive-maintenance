# ml/grey_box.py
# Estimates the calcaire (scale) thickness using Fourier conduction law.
# This is a physics-based soft sensor — no ML training required.
#
# Key formulas:
#   Q          = (flow_rate / N_molds) * rho * Cp * delta_T_measured
#   R_calcaire = delta_T_calcaire / Q
#   epaisseur  = R_calcaire * lambda * A   (meters, then converted to mm)

import math
import logging
from typing import Optional, Dict, Tuple

import config

log = logging.getLogger(__name__)

# Pipe internal lateral surface area
# A = pi * L * D
PIPE_AREA = math.pi * config.PIPE_LENGTH * config.PIPE_DIAMETER  # m^2


class GreyBoxModel:
    """
    Computes per-mold scale thickness in real time.

    Attributes:
        calibration_temps  : { mold_key: float } — T_mold on day 1 (clean pipe)
        delta_T_normal     : { mold_key: float } — T_heater - T_mold_jour1
    """

    def __init__(self):
        self.calibration_temps: Dict[Tuple, float] = {}
        self.delta_T_normal:    Dict[Tuple, float] = {}

    def set_calibration(self, group_id: int, mold_id: int, T_mold_jour1: float):
        """Store the day-1 calibration temperature for one mold."""
        key = (group_id, mold_id)
        self.calibration_temps[key] = T_mold_jour1
        self.delta_T_normal[key]    = round(config.T_HEATER - T_mold_jour1, 4)
        log.debug(
            "Calibration set mold (%d,%d): T_jour1=%.2f  delta_T_normal=%.4f",
            group_id, mold_id, T_mold_jour1, self.delta_T_normal[key]
        )

    def compute(
        self,
        group_id:   int,
        mold_id:    int,
        T_mold:     float,
        flow_lpm:   float,
    ) -> Dict:
        """
        Compute the scale metrics for one mold at one instant.

        Parameters:
            group_id  : mold group identifier
            mold_id   : mold identifier within the group
            T_mold    : current mold temperature (degrees C)
            flow_lpm  : total pump flow rate (L/min)

        Returns a dict with:
            delta_T_measured  : total thermal loss (degrees C)
            delta_T_calcaire  : loss due to scale only (degrees C)
            Q                 : heat flux per mold (Watts)
            R_calcaire        : thermal resistance of scale (degrees C / W)
            epaisseur_mm      : estimated scale thickness (mm)
            urgence           : urgency level string
            degradation_pct   : percentage toward the critical threshold
        """
        key = (group_id, mold_id)

        # Convert flow to m^3/s and split across all 12 molds
        flow_m3s    = (flow_lpm / 60.0) / 1000.0   # L/min -> m^3/s
        flow_mold   = flow_m3s / config.N_MOLDS

        delta_T_measured  = config.T_HEATER - T_mold
        delta_T_norm      = self.delta_T_normal.get(key, 1.5)   # default 1.5 if not calibrated

        # Thermal loss attributable to calcaire only (cannot be negative)
        delta_T_calcaire  = max(0.0, delta_T_measured - delta_T_norm)

        # Heat flux transported by water through this mold
        Q = flow_mold * config.RHO_WATER * config.CP_WATER * delta_T_measured
        Q = max(Q, 1e-6)   # avoid division by zero

        # Thermal resistance of the calcaire layer
        R_calcaire = delta_T_calcaire / Q

        # Estimated thickness in mm
        epaisseur_mm = R_calcaire * config.LAMBDA_CALCAIRE * PIPE_AREA * 1000.0

        # Urgency thresholds based on calibration
        delta_T_max   = (config.T_HEATER - config.T_MOLD_CRITICAL) - delta_T_norm
        delta_T_max   = max(delta_T_max, 0.1)   # safety

        degradation_pct = min((delta_T_calcaire / delta_T_max) * 100.0, 100.0)

        urgence = self._classify_urgency(T_mold)

        return {
            'delta_T_measured':  round(delta_T_measured,  4),
            'delta_T_calcaire':  round(delta_T_calcaire,  4),
            'Q':                 round(Q,                  2),
            'R_calcaire':        round(R_calcaire,         6),
            'epaisseur_mm':      round(epaisseur_mm,       4),
            'urgence':           urgence,
            'degradation_pct':   round(degradation_pct,    1),
        }

    @staticmethod
    def _classify_urgency(T_mold: float) -> str:
        if T_mold >= 43.5:
            return 'OK'
        elif T_mold >= 43.0:
            return 'FAIBLE'
        elif T_mold >= 42.5:
            return 'MOYEN'
        elif T_mold >= 42.0:
            return 'HAUTE'
        else:
            return 'URGENT'
