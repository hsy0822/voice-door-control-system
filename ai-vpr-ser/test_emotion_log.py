"""测试情感分析日志输出"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.engine import classify_emotion

# 创建一个测试音频文件路径（需要你提供一个实际的 wav 文件）
test_wav = Path("test_audio.wav")

if test_wav.exists():
    print(f"测试情感分析: {test_wav}")
    result = classify_emotion(test_wav)
    print("\n分析结果:")
    print(f"  情感: {result['emotion']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  胁迫检测: {result['duress']}")
    print(f"  原始标签: {result['label_raw']}")
else:
    print(f"测试文件不存在: {test_wav}")
    print("请提供一个 wav 音频文件用于测试")
