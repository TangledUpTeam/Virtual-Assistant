# 캐릭터 매뉴얼 (Live2D)

## 🎭 사용 가능한 모션

### 대기 모션
```javascript
model.motion('Idle');  // 기본 대기 동작 (3가지 중 랜덤)
```

### 클릭 반응
```javascript
model.motion('Tap');        // 일반 클릭
model.motion('Tap@Body');   // 몸 클릭 (특수)
```

### 튕기기
```javascript
model.motion('Flick');        // 일반 튕기기
model.motion('FlickDown');    // 아래로 튕기기  
model.motion('Flick@Body');   // 몸 튕기기
```

---

## 📍 위치

- **현재**: 화면 중앙-오른쪽 (75% 위치)
- **수정**: `index.html` 432번째 줄
  ```javascript
  model.position.set(canvasWidth * 0.75, canvasHeight - 50);
  ```

---

## 🔧 크기

- **현재**: 0.18 (18%)
- **수정**: `index.html` 425번째 줄
  ```javascript
  model.scale.set(0.18);
  ```

---

## ⌨️ 단축키

- `+/-` : 크기 조절
- **드래그** : 위치 이동
- **클릭** : Tap 모션 재생

---

## 📁 파일 위치

```
public/models/hiyori_free_ko/
├── runtime/
│   ├── hiyori_free_t08.model3.json  # 모델 정의
│   └── motion/
│       ├── hiyori_m01~m08.motion3.json  # 8개 모션
```

