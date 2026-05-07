function naturalSort(a, b) {
    return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
}

document.addEventListener('DOMContentLoaded', () => {
    const pdfFileInput = document.getElementById('pdfFileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const fileListEl = document.getElementById('fileList');
    const boreholeTitle = document.getElementById('boreholeTitle');
    const metaInfo = document.getElementById('metaInfo');
    const strataVisualizer = document.getElementById('strataVisualizer');
    const dataTableBody = document.getElementById('dataTableBody');
    const downloadCsvBtn = document.getElementById('downloadCsvBtn');
    const downloadJsonBtn = document.getElementById('downloadJsonBtn');
    const downloadCombinedCsvBtn = document.getElementById('downloadCombinedCsvBtn');
    const downloadZipBtn = document.getElementById('downloadZipBtn');
    const loadingOverlay = document.getElementById('loadingOverlay');

    let boreholesData = {};
    let rawCsvData = [];
    let currentCsvFilename = '';
    let currentJsonFilename = '';
    let currentDownloadUrl = '';
    let currentJsonDownloadUrl = '';
    let combinedCsvUrl = '';
    let zipUrl = '';
    let originalPdfName = '';

    // 1. PDF 업로드 & 백엔드(Flask) 풀스택 API 통신 모듈
    pdfFileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const formData = new FormData();
        // 다중 파일 추가
        for (let i = 0; i < files.length; i++) {
            formData.append('pdf_files', files[i]);
        }

        // 로딩 화면 ON
        loadingOverlay.style.display = 'flex';
        uploadStatus.textContent = `🚀 ${files.length}개의 파일을 변환 중입니다...`;

        // [Stage 50-Check] 프로토콜 체크 (file://로 직접 열 경우 서버 통신 불가 안내)
        if (window.location.protocol === 'file:') {
            alert('⚠️ 로컬 파일(file://)로 접속 중입니다.\n이 기능은 반드시 백엔드 서버가 필요합니다.\n\n[해결 방법]\n1. 서버(server.py)를 실행합니다.\n2. http://localhost:5000 주소로 접속해 주세요.');
            loadingOverlay.style.display = 'none';
            uploadStatus.textContent = '❌ 서버 접속 필요';
            pdfFileInput.value = '';
            return;
        }

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            console.log('--- Server Response Data ---', result);
            
            if (response.ok && result.results) {
                // 기존 데이터 초기화
                boreholesData = {};
                combinedCsvUrl = result.combined_csv_url;
                zipUrl = result.zip_url;
                
                let errorFiles = [];
                result.results.forEach(res => {
                    if (res.status === 'success') {
                        processServerData(res);
                    } else {
                        console.error(`파일 변환 실패 (${res.filename}):`, res.error);
                        errorFiles.push(res.filename);
                    }
                });
                
                if (errorFiles.length > 0) {
                    alert(`⚠️ 다음 파일의 변환에 실패했습니다:\n${errorFiles.join('\n')}\n\n데이터 형식을 확인해 주세요.`);
                }
                
                renderFileList();
                uploadStatus.textContent = '✅ 완료! 모든 파일의 데이터가 분석되었습니다.';
                
                // 전체 다운로드 버튼 노출
                if (combinedCsvUrl) downloadCombinedCsvBtn.style.display = 'block';
                if (zipUrl) downloadZipBtn.style.display = 'block';
            } else {
                alert('업로드 에러: ' + (result.error || '알 수 없는 에러'));
                uploadStatus.textContent = '❌ 변환 에러 발생';
            }
        } catch (error) {
            console.error('Fetch error:', error);
            alert('서버 통신 오류가 발생했습니다.');
            uploadStatus.textContent = '❌ 통신 에러';
        } finally {
            loadingOverlay.style.display = 'none';
            pdfFileInput.value = ''; 
        }
    });

    // 2. 서버에서 받은 개별 파일 결과를 프론트엔드 시각화 구조로 가공 및 병합
    function processServerData(res) {
        if (!res.data || !Array.isArray(res.data) || res.data.length === 0) {
            console.error(`[Data Error] ${res.filename}: 서버 결과(data)가 없거나 배열이 아닙니다. 응답:`, res);
            return;
        }

        const mergedArray = res.data;
        const filename = res.filename;
        const downloadUrl = res.download_url;
        const csvFilename = res.csv_filename;

        mergedArray.forEach((row, index) => {
            const holeNo = row['시추공명'];
            if (!holeNo) {
                console.error(`[Field Error] ${res.filename} - Row ${index}: '시추공명'이 누락되었습니다. 행 데이터:`, row);
                return;
            }

            // 프로젝트명과 시추공명을 조합하여 고유 ID 생성 (중복 방지)
            const boreholeId = (res.project_name || filename) + "||" + holeNo;

            if (!boreholesData[boreholeId]) {
                boreholesData[boreholeId] = {
                    holeNo: holeNo,
                    projectName: res.project_name || filename,
                    fileOrigin: filename,
                    downloadUrl: downloadUrl,
                    jsonDownloadUrl: res.json_download_url,
                    csvFilename: csvFilename,
                    jsonFilename: res.json_filename,
                    meta: {
                        경도: row['lon_wgs84'] || row['경도'] || 'N/A',
                        위도: row['lat_wgs84'] || row['위도'] || 'N/A',
                        표고: row['표고'] || 'N/A',
                        지하수위: row['지하수위'] || 'N/A'
                    },
                    layers: []
                };
            }

            const top = parseFloat(row['상심도']);
            const bottom = parseFloat(row['하심도']);
            const soil = row['지층명'];

            if (!soil || isNaN(top) || isNaN(bottom)) {
                console.error(`[Field Error] ${boreholeId} - Row ${index}: 지층 매핑 필수 데이터(지층명/상심도/하심도)가 누락 또는 형식이 잘못되었습니다.`, row);
            } else {
                boreholesData[boreholeId].layers.push({
                    soilType: soil,
                    top: top,
                    bottom: bottom,
                    thickness: parseFloat((bottom - top).toFixed(2))
                });
            }
        });
    }

    // 3. 우측 사이드바 렌더링 (프로젝트별 그룹화 및 자연 정렬 적용)
    function renderFileList() {
        fileListEl.innerHTML = '';
        
        // 프로젝트(파일)별로 그룹화
        const groups = {};
        Object.keys(boreholesData).forEach(id => {
            const data = boreholesData[id];
            const origin = data.projectName || data.fileOrigin;
            if (!groups[origin]) groups[origin] = [];
            groups[origin].push(id);
        });

        // 프로젝트별 자연 정렬
        Object.keys(groups).sort(naturalSort).forEach(origin => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'project-header';
            groupDiv.textContent = origin;
            fileListEl.appendChild(groupDiv);
            
            groups[origin].sort(naturalSort).forEach(id => {
                const li = document.createElement('div');
                li.className = 'file-item';
                li.innerHTML = `<div class="file-item-title">${boreholesData[id].holeNo}</div>`;
                li.onclick = () => {
                    document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
                    li.classList.add('active');
                    viewBorehole(id);
                };
                fileListEl.appendChild(li);
            });
        });
        
        const firstId = Object.keys(boreholesData)[0];
        if (firstId) {
            const firstItem = fileListEl.querySelector('.file-item');
            if (firstItem) firstItem.classList.add('active');
            viewBorehole(firstId);
        }
    }

    // 4. 시추주상도 기둥 그래픽 & 테이블 동기화 렌더링
    function viewBorehole(id) {
        const data = boreholesData[id];
        if (!data) return;

        currentDownloadUrl = data.downloadUrl;
        currentCsvFilename = data.csvFilename || "seoul_borehole_master.csv";
        
        currentJsonDownloadUrl = data.jsonDownloadUrl;
        currentJsonFilename = data.jsonFilename || `${data.projectName}.json`;
        
        boreholeTitle.innerHTML = `<span>${data.holeNo}</span> <small style="font-size: 0.6em; color: #94a3b8;">(${data.projectName || data.fileOrigin})</small>`;
        downloadCsvBtn.style.display = 'block'; 
        if (downloadJsonBtn) downloadJsonBtn.style.display = 'block';
        
        metaInfo.innerHTML = `
            <div class="meta-item"><strong>경도:</strong> ${data.meta.경도 || '-'}</div>
            <div class="meta-item"><strong>위도:</strong> ${data.meta.위도 || '-'}</div>
            <div class="meta-item"><strong>표고:</strong> ${data.meta.표고 || '-'}</div>
            <div class="meta-item"><strong>지하수위:</strong> ${data.meta.지하수위 || '-'}</div>
        `;

        strataVisualizer.innerHTML = '';
        dataTableBody.innerHTML = '';

        if (!data.layers || data.layers.length === 0) {
            strataVisualizer.innerHTML = '<p class="placeholder-text" style="color: #ef4444;">❌ 이 시추공에서는 유효한 지층 데이터를 찾을 수 없습니다.</p>';
            dataTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8;">데이터가 존재하지 않습니다.</td></tr>';
            return;
        }

        // [1] 상심도 기준 오름차순 정렬 및 부적절한 데이터 필터링 [NEW]
        const sortedLayers = [...data.layers].sort((a, b) => a.top - b.top);
        
        let lastValidBottom = -1;
        const filteredLayers = sortedLayers.filter(layer => {
            // 논리적 필터: 심도 역전, 두께 0 이하, 중간 0.0 리셋 행 제외
            if (layer.thickness <= 0) return false;
            if (layer.top < lastValidBottom) return false;
            if (layer.top === 0 && lastValidBottom > 0) return false;
            
            lastValidBottom = layer.bottom;
            return true;
        });

        const maxDepth = filteredLayers[filteredLayers.length - 1]?.bottom || 100;

        filteredLayers.forEach(layer => {
            // [Stage 47] 백엔드에서 4대 대분류로 정규화되어 도착하므로 1:1 완전일치 매핑
            const COLOR_MAP = { '토사': 'soil', '풍화암': 'weathered', '연암': 'ripping', '경암': 'blasting' };
            const colorKey = COLOR_MAP[layer.soilType] || 'soil';

            const div = document.createElement('div');
            div.className = `strata-layer ${layer.soilType}`;
            div.style.background = `var(--color-${colorKey})`; 
            
            const heightPercent = Math.max((layer.thickness / maxDepth) * 100, 5); 
            div.style.height = `${heightPercent}%`;
            div.textContent = layer.soilType;
            div.title = `[분류] ${layer.soilType} / 구간: ${layer.top}m ~ ${layer.bottom}m`;

            strataVisualizer.appendChild(div);

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 600;">
                    <span style="display:inline-block; width:14px; height:14px; border-radius:50%; vertical-align: middle; background:var(--color-${colorKey}); margin-right:10px; box-shadow: 0 0 10px var(--color-${colorKey});"></span>
                    ${layer.soilType}
                </td>
                <td>${layer.top.toFixed(2)}</td>
                <td>${layer.bottom.toFixed(2)}</td>
                <td style="color: var(--accent-color); font-weight: bold;">+ ${layer.thickness.toFixed(2)}</td>
            `;
            dataTableBody.appendChild(tr);
        });
    }

    // 5. 다운로드 안정화 엔진 (표준 HTTP 방식 채택 - Stage 45-Q)
    function triggerDownload(url, defaultName) {
        if (!url) {
            console.error('❌ [Download] URL이 존재하지 않습니다.');
            return;
        }
        
        console.log(`🚀 [Download] 표준 전송 시작: ${url}`);
        
        // [Stage 45-Q] Gemini 권고안 반영: blob: URL 대신 정규 서버 URL을 직접 사용
        // server.py에서 이미 Content-Type: utf-8-sig 및 Content-Disposition을 완벽히 주입함.
        // 이 방식은 브라우저 탭 세션에 종속되지 않으며 전송 엔진 중 가장 안정적임.
        try {
            const link = document.createElement('a');
            // 캐시 방지를 위해 타임스탬프 쿼리 스트링 추가
            const finalUrl = url + (url.includes('?') ? '&' : '?') + `t=${new Date().getTime()}`;
            link.href = finalUrl;
            link.download = defaultName; // 서버 헤더가 우선되나 폴백용으로 지정
            
            document.body.appendChild(link);
            link.click();
            
            // 전송 트리거 후 클린업
            setTimeout(() => {
                document.body.removeChild(link);
                console.log('✅ [Download] 표준 전송 트리거 완료.');
            }, 500);
            
        } catch (error) {
            console.warn('⚠️ [Download] 표준 전송 실패, 브라우저 직접 내비게이션 폴백 시도:', error);
            window.location.href = url;
        }
    }

    downloadCsvBtn.addEventListener('click', () => {
        triggerDownload(currentDownloadUrl, currentCsvFilename || "result.csv");
    });

    if (downloadJsonBtn) {
        downloadJsonBtn.addEventListener('click', () => {
            triggerDownload(currentJsonDownloadUrl, currentJsonFilename || "result.json");
        });
    }

    downloadCombinedCsvBtn.addEventListener('click', () => {
        triggerDownload(combinedCsvUrl, "seoul_borehole_master.csv");
    });

    downloadZipBtn.addEventListener('click', () => {
        triggerDownload(zipUrl, "전체_결과_압축.zip");
    });
});
