import mediapipe as mp
print('mediapipe file:', getattr(mp, '__file__', 'built-in or no __file__'))
print('has solutions:', hasattr(mp, 'solutions'))
print('attrs sample:', [a for a in dir(mp) if not a.startswith('_')][:60])
