# backend/models/tft.py

import os
import numpy as np
import onnxruntime as ort


class TFTModelWrapper:
    """
    Wrapper for the TFT ONNX model stored in models_to_deploy/tft_model.onnx.
    Provides a simple predict() method.
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "models_to_deploy", "tft_model.onnx")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"TFT model not found at: {model_path}")

        # Load ONNX model
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

        # Get input name
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, series, horizon: int = 5):
        """
        series: list of floats (historical prices)
        horizon: number of future steps to predict

        Returns: list of predictions
        """

        if len(series) == 0:
            raise ValueError("Input series is empty.")

        # Convert to numpy array
        arr = np.array(series, dtype=np.float32).reshape(1, -1, 1)

        preds = []
        last_seq = arr.copy()

        for _ in range(horizon):
            output = self.session.run(None, {self.input_name: last_seq})
            next_val = float(output[0][0][0])
            preds.append(next_val)

            # Slide window
            last_seq = np.concatenate(
                [last_seq[:, 1:, :], np.array([[[next_val]]], dtype=np.float32)],
                axis=1
            )

        return preds


def TFTModel():
    return TFTModelWrapper()
