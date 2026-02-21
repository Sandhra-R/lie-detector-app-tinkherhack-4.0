import cv2
import numpy as np
import librosa
import random
import time

# Make mediapipe optional since it may not be available on all systems
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except (ImportError, ModuleNotFoundError):
    print("[Analyzer] WARNING: mediapipe not available - running in demo mode")
    mp = None
    HAS_MEDIAPIPE = False

class StressAnalyzer:
    def __init__(self):
        # mediapipe versions vary: if `solutions` isn't available (newer "tasks" API),
        # gracefully disable face analysis so the server can still run.
        self.face_mesh = None
        if HAS_MEDIAPIPE:
            try:
                print("[Analyzer] Attempting to use mediapipe.solutions...")
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                print("[Analyzer] ✓ MediaPipe Face Mesh initialized successfully")
            except AttributeError as e:
                print(f"[Analyzer] ✗ MediaPipe solutions not available: {e}")
                print("[Analyzer] → Using demo/simulation mode (realistic test data)")
                self.face_mesh = None
            except Exception as e:
                print(f"[Analyzer] ✗ MediaPipe error: {e}")
                print("[Analyzer] → Using demo/simulation mode")
                self.face_mesh = None
        else:
            print("[Analyzer] → Using demo/simulation mode (realistic test data)")
        
        self.blink_count = 0
        self.is_eye_closed = False
        self.EAR_THRESHOLD = 0.2
        self.demo_mode = self.face_mesh is None
        self.frame_count = 0
        self.last_blink_time = time.time()
        
        # Eye landmarks
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
        # Facial expression landmarks
        self.LEFT_EYEBROW = [70, 63, 105, 66, 107]
        self.RIGHT_EYEBROW = [336, 296, 334, 293, 300]
        self.MOUTH = [61, 291, 0, 17, 269, 270, 409, 291]
        self.NOSE_TIP = 4
        self.LEFT_EYE_INNER = 133
        self.RIGHT_EYE_INNER = 362

    def calculate_ear(self, landmarks, eye_indices):
        vertical1 = np.linalg.norm(
            np.array(landmarks[eye_indices[1]]) - np.array(landmarks[eye_indices[5]])
        )
        vertical2 = np.linalg.norm(
            np.array(landmarks[eye_indices[2]]) - np.array(landmarks[eye_indices[4]])
        )
        horizontal = np.linalg.norm(
            np.array(landmarks[eye_indices[0]]) - np.array(landmarks[eye_indices[3]])
        )
        # Protect against division by zero
        eps = 1e-6
        return (vertical1 + vertical2) / (2.0 * (horizontal + eps))

    def analyze_frame(self, frame):
        data = {
            "blink_count": self.blink_count,
            "ear": 0.0,
            "stress_level": "low",
            "demo_mode": self.face_mesh is None,
            "expression": "neutral",
            "gaze_shift": False
        }

        # If mediapipe FaceMesh isn't available, use demo/simulation mode
        if self.face_mesh is None:
            return self._demo_analyze_frame(data)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                h, w = frame.shape[:2]
                points = []
                for lm in face_landmarks.landmark:
                    points.append([lm.x, lm.y, lm.z])
                
                # --- EYE ASPECT RATIO (blink detection) ---
                left_ear = self.calculate_ear(points, self.LEFT_EYE)
                right_ear = self.calculate_ear(points, self.RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0
                
                if ear < self.EAR_THRESHOLD:
                    if not self.is_eye_closed:
                        self.is_eye_closed = True
                else:
                    if self.is_eye_closed:
                        self.blink_count += 1
                        self.is_eye_closed = False
                
                data["ear"] = float(ear)
                data["blink_count"] = self.blink_count
                
                # --- EYEBROW RAISE DETECTION (surprise/stress) ---
                try:
                    left_brow_y = np.mean([points[i][1] for i in self.LEFT_EYEBROW])
                    right_brow_y = np.mean([points[i][1] for i in self.RIGHT_EYEBROW])
                    left_eye_y = points[self.LEFT_EYE[0]][1]
                    right_eye_y = points[self.RIGHT_EYE[0]][1]
                    
                    # Distance between eyebrow and eye (normalized)
                    left_brow_dist = left_eye_y - left_brow_y
                    right_brow_dist = right_eye_y - right_brow_y
                    avg_brow_raise = (left_brow_dist + right_brow_dist) / 2.0
                    
                    data["brow_raise"] = float(avg_brow_raise)
                    data["eyebrow_raised"] = bool(avg_brow_raise > 0.04)  # raised eyebrows = surprise/stress
                except Exception:
                    data["brow_raise"] = 0.0
                    data["eyebrow_raised"] = False
                
                # --- MOUTH TENSION (lip compression) ---
                try:
                    mouth_top = points[0][1]   # upper lip
                    mouth_bot = points[17][1]   # lower lip
                    mouth_left = points[61][0]
                    mouth_right = points[291][0]
                    mouth_height = abs(mouth_bot - mouth_top)
                    mouth_width = abs(mouth_right - mouth_left)
                    mouth_ratio = mouth_height / (mouth_width + 1e-6)
                    data["mouth_tension"] = bool(mouth_ratio < 0.15)  # tight lips = stress
                    data["mouth_openness"] = float(mouth_ratio)
                except Exception:
                    data["mouth_tension"] = False
                    data["mouth_openness"] = 0.0
                
                # --- GAZE DIRECTION (looking away = possible deception) ---
                try:
                    nose_x = points[self.NOSE_TIP][0]
                    face_center_x = np.mean([points[i][0] for i in [234, 454]])  # cheek points
                    gaze_offset = abs(nose_x - face_center_x)
                    data["gaze_shift"] = bool(gaze_offset > 0.05)
                    data["gaze_offset"] = float(gaze_offset)
                except Exception:
                    data["gaze_shift"] = False
                    data["gaze_offset"] = 0.0

                # --- DETERMINE EXPRESSION ---
                expression = "neutral"
                if data.get("eyebrow_raised") and ear < 0.22:
                    expression = "fear/surprise"
                elif data.get("eyebrow_raised"):
                    expression = "surprise"
                elif data.get("mouth_tension"):
                    expression = "tense"
                elif data.get("gaze_shift"):
                    expression = "avoidant"
                data["expression"] = expression
                
                # --- STRESS CALCULATION (combined signals) ---
                stress_signals = 0
                if self.blink_count > 30:
                    stress_signals += 2
                elif self.blink_count > 15:
                    stress_signals += 1
                if data.get("eyebrow_raised"):
                    stress_signals += 1
                if data.get("mouth_tension"):
                    stress_signals += 1
                if data.get("gaze_shift"):
                    stress_signals += 1
                    
                if stress_signals >= 3:
                    data["stress_level"] = "high"
                elif stress_signals >= 1:
                    data["stress_level"] = "medium"
                else:
                    data["stress_level"] = "low"
        
        return data

    def _demo_analyze_frame(self, data):
        """Simulate realistic eye tracking and stress data for demo purposes"""
        self.frame_count += 1
        
        # Simulate realistic blink pattern
        if self.frame_count % 70 == 0:
            self.blink_count += 1
        
        # Simulate EAR with slight variation
        base_ear = 0.25 + random.uniform(-0.05, 0.08)
        data["ear"] = max(0.1, min(0.40, base_ear))
        
        # Simulate facial expressions cycling through states
        expressions = ["neutral", "tense", "avoidant", "surprise"]
        data["expression"] = expressions[(self.frame_count // 100) % len(expressions)]
        data["eyebrow_raised"] = (self.frame_count % 150 < 20)
        data["mouth_tension"] = (self.frame_count % 200 < 30)
        data["gaze_shift"] = (self.frame_count % 120 < 15)
        data["brow_raise"] = 0.05 if data["eyebrow_raised"] else 0.02
        data["gaze_offset"] = 0.06 if data["gaze_shift"] else 0.01
        data["demo_mode"] = True
        
        # Simulate stress level based on blinks
        if self.blink_count > 25:
            data["stress_level"] = "high"
        elif self.blink_count > 12:
            data["stress_level"] = "medium"
        else:
            data["stress_level"] = "low"
        
        data["blink_count"] = self.blink_count
        
        return data

    def analyze_audio(self, audio_path):
        """
        Advanced audio analysis for detecting stress and potential deception indicators.
        Measures: pitch, variance, speech rate, energy, hesitations, and stress level.
        """
        try:
            y, sr = librosa.load(audio_path, sr=22050)
            
            # 1. PITCH ANALYSIS
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'), sr=sr
            )
            if f0 is None:
                return {"status": "no_voice"}

            f0_valid = f0[~np.isnan(f0)]
            if len(f0_valid) == 0:
                return {"status": "no_voice"}
            
            avg_pitch = float(np.mean(f0_valid))
            pitch_variance = float(np.var(f0_valid))
            pitch_std = float(np.std(f0_valid))
            
            # 2. MFCC ANALYSIS (Speech characteristics)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
            
            # 3. ENERGY ANALYSIS (Intensity/Stress)
            S = librosa.magphase(librosa.stft(y))[0]
            energy = np.sqrt(np.sum(S**2, axis=0))
            energy_mean = float(np.mean(energy))
            energy_std = float(np.std(energy))
            energy_max = float(np.max(energy))
            
            # 4. SPEECH RATE (Phoneme density)
            # Use spectral centroid as proxy for speech articulation
            spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spec_centroid_mean = float(np.mean(spec_centroid))
            spec_centroid_std = float(np.std(spec_centroid))
            
            # 5. SILENCE/HESITATION DETECTION
            # Frames with low energy indicate pauses/hesitations
            silence_threshold = energy_mean * 0.3
            silent_frames = np.sum(energy < silence_threshold)
            total_frames = len(energy)
            silence_ratio = float(silent_frames / total_frames) if total_frames > 0 else 0
            
            # 6. ZERO CROSSING RATE (Fricatives/consonants - stress indicator)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_mean = float(np.mean(zcr))
            zcr_std = float(np.std(zcr))
            
            # 7. CALCULATE STRESS & TRUTH INDICATORS
            stress_score = self._calculate_stress_score(
                avg_pitch, pitch_std, energy_std, energy_max, 
                silence_ratio, zcr_std, spec_centroid_std
            )
            
            truth_likelihood = self._calculate_truth_likelihood(
                avg_pitch, pitch_variance, pitch_std,
                energy_mean, energy_std, silence_ratio,
                spec_centroid_std, zcr_std
            )
            
            return {
                "status": "analyzed",
                "avg_pitch": avg_pitch,
                "pitch_variance": pitch_variance,
                "pitch_std": pitch_std,
                "energy_mean": energy_mean,
                "energy_std": energy_std,
                "energy_max": energy_max,
                "silence_ratio": silence_ratio,
                "zcr_mean": zcr_mean,
                "zcr_std": zcr_std,
                "spectral_centroid": spec_centroid_mean,
                "stress_level": "high" if stress_score > 0.7 else "medium" if stress_score > 0.4 else "low",
                "stress_score": float(stress_score),
                "truth_likelihood": float(truth_likelihood),
                "truth_indicator": "LIKELY TRUTHFUL" if truth_likelihood > 0.6 else "UNCERTAIN" if truth_likelihood > 0.4 else "POSSIBLE DECEPTION"
            }
        except Exception as e:
            print(f"[Analyzer Audio Error] {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_stress_score(self, avg_pitch, pitch_std, energy_std, energy_max, silence_ratio, zcr_std, spec_std):
        """
        Calculate stress score (0-1) based on vocal characteristics.
        Higher score = more stress indicators detected.
        """
        stress_components = []
        
        # Pitch variation (higher std = more stress)
        pitch_stress = min(pitch_std / 50.0, 1.0)  # Normalize
        stress_components.append(pitch_stress * 0.25)
        
        # Energy variation (higher std = more stress/animation)
        energy_stress = min(energy_std / 3000.0, 1.0)
        stress_components.append(energy_stress * 0.25)
        
        # Hesitation/silence (higher ratio = more hesitation = stress)
        silence_stress = min(silence_ratio / 0.5, 1.0)  # Normalize to 50% silence
        stress_components.append(silence_stress * 0.25)
        
        # Articulation sharpness (higher ZCR std = more variation = stress)
        articulation_stress = min(zcr_std / 0.05, 1.0)
        stress_components.append(articulation_stress * 0.25)
        
        return min(np.mean(stress_components), 1.0)
    
    def _calculate_truth_likelihood(self, avg_pitch, pitch_variance, pitch_std, energy_mean, energy_std, 
                                     silence_ratio, spec_std, zcr_std):
        """
        Calculate likelihood of truth (0-1).
        Based on psychological acoustic indicators of stress and deception.
        
        Deception indicators:
        - Excessive pitch variance (nervous)
        - High silence ratio (hesitation)
        - Inconsistent energy (uncertainty)
        - Extreme spectral values (stress)
        """
        truth_score = 1.0
        
        # High pitch variance suggests stress/nervousness
        if pitch_std > 40:  # High variance
            truth_score -= 0.15
        elif pitch_std < 10:  # Very low variance (unnatural)
            truth_score -= 0.10
        else:
            truth_score += 0.05  # Natural variance = good
        
        # Excessive hesitation/silence suggests deception
        if silence_ratio > 0.4:
            truth_score -= 0.20
        elif silence_ratio < 0.15:
            truth_score += 0.05  # Fluent speech
        
        # Energy consistency
        if energy_std > 2000:  # Very inconsistent
            truth_score -= 0.10
        else:
            truth_score += 0.05
        
        # Spectral variation (too much = stress indicators)
        if spec_std > 800:
            truth_score -= 0.10
        
        # ZCR variation (consonant variation)
        if zcr_std > 0.08:  # Very high variation
            truth_score -= 0.10
        
        # Average pitch (females typically 150-250 Hz, males 75-150 Hz)
        # Extreme values suggest stress
        if avg_pitch < 50 or avg_pitch > 400:
            truth_score -= 0.05
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, truth_score))

    def reset(self):
        self.blink_count = 0
        self.is_eye_closed = False