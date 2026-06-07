import requests

REST_API_KEY = "85c3a19945eb6dc379dcf148b1f4455c"

def test_kakao_reverse_geocoding(lat, lng):
    # 역지오코딩 엔드포인트로 변경
    url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
    headers = {"Authorization": f"KakaoAK {REST_API_KEY}"}

    # x(경도), y(위도) 순서로 넣어야 함
    params = {"x": lng, "y": lat}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        print("--- 역지오코딩 응답 성공! ---")
        if data['documents']:
            # 도로명 주소와 지번 주소 중 원하는 것을 가져오면 됨
            addr_info = data['documents'][0]
            print(f"주소: {addr_info['address']['address_name']}")
        else:
            print("해당 좌표에 주소 정보가 없습니다.")
    else:
        print(f"에러 발생! 상태 코드: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # 테스트용 좌표 (예: 서울시청 부근)
    test_kakao_reverse_geocoding(37.5666805, 126.9784147)