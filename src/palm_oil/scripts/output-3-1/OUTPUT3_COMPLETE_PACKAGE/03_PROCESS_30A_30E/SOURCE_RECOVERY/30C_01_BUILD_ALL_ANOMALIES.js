// ==========================================================
// 30C-01
// ANOMALI BASELINE 2020–2024 VS MONITORING 2025
// SELURUH 6 PERIODE
//
// OUTPUT:
// - Anomali indeks Sentinel-2
// - Penurunan indeks Sentinel-2
// - Perubahan Sentinel-1
// - Magnitudo perubahan Sentinel-1
// - Validitas dan confidence data
//
// CATATAN:
// Ini merupakan anomaly layer.
// Belum menjadi kelas kesehatan atau diagnosis.
// ==========================================================


// ==========================================================
// 1. KONFIGURASI
// ==========================================================

// false = pemeriksaan tanpa membuat task.
// true  = membuat 6 task ekspor.
var EXPORT_RESULTS = true;

// Periode yang ditampilkan pada peta.
var DISPLAY_PERIOD = 'P01_JAN_FEB';

// Minimum kualitas data.
var MIN_S2_BASE_VALID_YEARS = 3;
var MIN_S2_MON_CLEAR_DAYS = 2;

var MIN_S1_BASE_VALID_YEARS = 3;
var MIN_S1_MON_DATE_COUNT = 3;


// ==========================================================
// 2. LOKASI ASSET
// ==========================================================

var ASSET_ROOT =
  'projects/palm-oil-503202/assets/';

var BOUNDARY_ASSET =
  ASSET_ROOT +
  'SIAK_AOI01_PLANTATION_BOUNDARY_WEB_WGS84_2025';


// ==========================================================
// 3. DAFTAR PERIODE
// ==========================================================

var PERIODS = [
  'P01_JAN_FEB',
  'P02_MAR_APR',
  'P03_MAY_JUN',
  'P04_JUL_AUG',
  'P05_SEP_OCT',
  'P06_NOV_DEC'
];


// ==========================================================
// 4. PLANTATION BOUNDARY
// ==========================================================

var plantationBoundary =
  ee.FeatureCollection(BOUNDARY_ASSET);

var geometry =
  plantationBoundary.geometry();

Map.centerObject(
  plantationBoundary,
  11
);

Map.addLayer(
  plantationBoundary.style({
    color: 'FFFF00',
    fillColor: '00000000',
    width: 2
  }),
  {},
  'Plantation Boundary',
  true
);


// ==========================================================
// 5. FUNGSI PEMBUATAN ANOMALI
// ==========================================================

function buildAnomaly(periodName) {

  // --------------------------------------------------------
  // 5.1. MEMBACA ASSET 30B
  // --------------------------------------------------------

  var baselineAsset =
    ASSET_ROOT +
    'SIAK_AOI01_O3_30B_BASELINE_' +
    periodName;

  var monitoringAsset =
    ASSET_ROOT +
    'SIAK_AOI01_O3_30B_MONITORING_2025_' +
    periodName;

  var baseline =
    ee.Image(baselineAsset);

  var monitoring =
    ee.Image(monitoringAsset);


  // --------------------------------------------------------
  // 5.2. BAND QA
  // --------------------------------------------------------

  var s2BaseValidYears =
    baseline
      .select('S2_BASE_VALID_YEARS')
      .rename('S2_BASE_VALID_YEARS')
      .unmask(0);

  var s2MonClearDays =
    monitoring
      .select('S2_MON_CLEAR_DAYS')
      .rename('S2_MON_CLEAR_DAYS')
      .unmask(0);

  var s1BaseValidYears =
    baseline
      .select('S1_BASE_VALID_YEARS')
      .rename('S1_BASE_VALID_YEARS')
      .unmask(0);

  var s1MonDateCount =
    monitoring
      .select('S1_MON_DATE_COUNT')
      .rename('S1_MON_DATE_COUNT')
      .unmask(0);


  // --------------------------------------------------------
  // 5.3. VALIDITAS DATA
  // --------------------------------------------------------

  var s2Valid =
    s2BaseValidYears
      .gte(MIN_S2_BASE_VALID_YEARS)
      .and(
        s2MonClearDays.gte(
          MIN_S2_MON_CLEAR_DAYS
        )
      )
      .rename('S2_VALID');

  var s1Valid =
    s1BaseValidYears
      .gte(MIN_S1_BASE_VALID_YEARS)
      .and(
        s1MonDateCount.gte(
          MIN_S1_MON_DATE_COUNT
        )
      )
      .rename('S1_VALID');


  // --------------------------------------------------------
  // 5.4. ANOMALI SENTINEL-2
  //
  // ANOMALI = MONITORING 2025 − BASELINE
  //
  // Nilai negatif menunjukkan penurunan.
  // --------------------------------------------------------

  var anomNdvi =
    monitoring
      .select('S2_MON_NDVI')
      .subtract(
        baseline.select('S2_BASE_NDVI')
      )
      .rename('ANOM_NDVI')
      .updateMask(s2Valid);

  var anomEvi =
    monitoring
      .select('S2_MON_EVI')
      .subtract(
        baseline.select('S2_BASE_EVI')
      )
      .rename('ANOM_EVI')
      .updateMask(s2Valid);

  var anomMsavi =
    monitoring
      .select('S2_MON_MSAVI')
      .subtract(
        baseline.select('S2_BASE_MSAVI')
      )
      .rename('ANOM_MSAVI')
      .updateMask(s2Valid);

  var anomNdre =
    monitoring
      .select('S2_MON_NDRE')
      .subtract(
        baseline.select('S2_BASE_NDRE')
      )
      .rename('ANOM_NDRE')
      .updateMask(s2Valid);

  var anomNdmi =
    monitoring
      .select('S2_MON_NDMI')
      .subtract(
        baseline.select('S2_BASE_NDMI')
      )
      .rename('ANOM_NDMI')
      .updateMask(s2Valid);


  // --------------------------------------------------------
  // 5.5. PENURUNAN SENTINEL-2
  //
  // Penurunan dibuat positif:
  // DECLINE = max(BASELINE − MONITORING, 0)
  //
  // Nilai 0 berarti tidak terjadi penurunan.
  // --------------------------------------------------------

  var declineNdvi =
    anomNdvi
      .multiply(-1)
      .max(0)
      .rename('DECLINE_NDVI');

  var declineEvi =
    anomEvi
      .multiply(-1)
      .max(0)
      .rename('DECLINE_EVI');

  var declineMsavi =
    anomMsavi
      .multiply(-1)
      .max(0)
      .rename('DECLINE_MSAVI');

  var declineNdre =
    anomNdre
      .multiply(-1)
      .max(0)
      .rename('DECLINE_NDRE');

  var declineNdmi =
    anomNdmi
      .multiply(-1)
      .max(0)
      .rename('DECLINE_NDMI');


  // --------------------------------------------------------
  // 5.6. ANOMALI SENTINEL-1
  //
  // Nilai positif/negatif hanya menunjukkan perubahan.
  // Belum langsung dianggap penurunan kondisi.
  // --------------------------------------------------------

  var anomVv =
    monitoring
      .select('S1_MON_VV_DB')
      .subtract(
        baseline.select('S1_BASE_VV_DB')
      )
      .rename('ANOM_VV_DB')
      .updateMask(s1Valid);

  var anomVh =
    monitoring
      .select('S1_MON_VH_DB')
      .subtract(
        baseline.select('S1_BASE_VH_DB')
      )
      .rename('ANOM_VH_DB')
      .updateMask(s1Valid);

  var anomVvMinusVh =
    monitoring
      .select('S1_MON_VV_MINUS_VH_DB')
      .subtract(
        baseline.select(
          'S1_BASE_VV_MINUS_VH_DB'
        )
      )
      .rename('ANOM_VV_MINUS_VH_DB')
      .updateMask(s1Valid);

  var anomS1Rvi =
    monitoring
      .select('S1_MON_RVI')
      .subtract(
        baseline.select('S1_BASE_RVI')
      )
      .rename('ANOM_S1_RVI')
      .updateMask(s1Valid);


  // --------------------------------------------------------
  // 5.7. MAGNITUDO PERUBAHAN SENTINEL-1
  //
  // Nilai absolut menunjukkan seberapa besar perubahan,
  // tanpa menentukan arah perubahan.
  // --------------------------------------------------------

  var absChangeVv =
    anomVv
      .abs()
      .rename('ABS_CHANGE_VV_DB');

  var absChangeVh =
    anomVh
      .abs()
      .rename('ABS_CHANGE_VH_DB');

  var absChangeVvMinusVh =
    anomVvMinusVh
      .abs()
      .rename('ABS_CHANGE_VV_MINUS_VH_DB');

  var absChangeS1Rvi =
    anomS1Rvi
      .abs()
      .rename('ABS_CHANGE_S1_RVI');


  // --------------------------------------------------------
  // 5.8. CONFIDENCE SENTINEL-2
  //
  // 0 = tidak valid
  // 1 = rendah
  // 2 = sedang
  // 3 = tinggi
  // --------------------------------------------------------

  var s2Confidence =
    ee.Image.constant(0)

      // Rendah: 2–3 clear days
      .where(
        s2Valid
          .and(s2MonClearDays.gte(2))
          .and(s2MonClearDays.lte(3)),
        1
      )

      // Sedang: 4–5 clear days
      .where(
        s2Valid
          .and(s2MonClearDays.gte(4))
          .and(s2MonClearDays.lte(5)),
        2
      )

      // Tinggi: minimal 6 clear days
      .where(
        s2Valid
          .and(s2MonClearDays.gte(6)),
        3
      )

      .rename('S2_CONFIDENCE');


  // --------------------------------------------------------
  // 5.9. CONFIDENCE SENTINEL-1
  //
  // 0 = tidak valid
  // 1 = rendah
  // 2 = sedang
  // 3 = tinggi
  // --------------------------------------------------------

  var s1Confidence =
    ee.Image.constant(0)

      // Rendah: 3 tanggal
      .where(
        s1Valid
          .and(s1MonDateCount.eq(3)),
        1
      )

      // Sedang: 4–5 tanggal
      .where(
        s1Valid
          .and(s1MonDateCount.gte(4))
          .and(s1MonDateCount.lte(5)),
        2
      )

      // Tinggi: minimal 6 tanggal
      .where(
        s1Valid
          .and(s1MonDateCount.gte(6)),
        3
      )

      .rename('S1_CONFIDENCE');


  // --------------------------------------------------------
  // 5.10. CONFIDENCE DATA GABUNGAN
  //
  // Ini confidence ketersediaan data,
  // bukan confidence diagnosis tanaman.
  // --------------------------------------------------------

  var dataConfidence =
    s2Confidence
      .add(s1Confidence)
      .divide(2)
      .rename('DATA_CONFIDENCE');


  // --------------------------------------------------------
  // 5.11. OUTPUT FINAL PER PERIODE
  // --------------------------------------------------------

  var anomalyOutput =
    ee.Image.cat([

      // Anomali optik
      anomNdvi,
      anomEvi,
      anomMsavi,
      anomNdre,
      anomNdmi,

      // Penurunan optik
      declineNdvi,
      declineEvi,
      declineMsavi,
      declineNdre,
      declineNdmi,

      // Anomali radar
      anomVv,
      anomVh,
      anomVvMinusVh,
      anomS1Rvi,

      // Magnitudo perubahan radar
      absChangeVv,
      absChangeVh,
      absChangeVvMinusVh,
      absChangeS1Rvi,

      // QA
      s2BaseValidYears,
      s2MonClearDays,
      s1BaseValidYears,
      s1MonDateCount,
      s2Valid,
      s1Valid,
      s2Confidence,
      s1Confidence,
      dataConfidence

    ])
    .toFloat()
    .clip(geometry)
    .set({

      AOI_ID:
        'SIAK_AOI01',

      PERIOD:
        periodName,

      BASELINE:
        '2020-2024',

      MONITORING_YEAR:
        2025,

      ANOMALY_FORMULA:
        'MONITORING_MINUS_BASELINE',

      PRODUCT_TYPE:
        'PLANTATION_CONDITION_ANOMALY',

      MODEL_STAGE:
        '30C'

    });

  return anomalyOutput;
}


// ==========================================================
// 6. MEMBENTUK SELURUH PERIODE
// ==========================================================

var anomalyOutputs = {};

PERIODS.forEach(function(periodName) {

  anomalyOutputs[periodName] =
    buildAnomaly(periodName);

});


// ==========================================================
// 7. OUTPUT YANG DITAMPILKAN
// ==========================================================

var displayOutput =
  anomalyOutputs[DISPLAY_PERIOD];


// ==========================================================
// 8. TABEL RINGKASAN
// ==========================================================

var summaryFeatures =
  PERIODS.map(function(periodName) {

    return ee.Feature(null, {

      PERIOD:
        periodName,

      BASELINE_ASSET:
        ASSET_ROOT +
        'SIAK_AOI01_O3_30B_BASELINE_' +
        periodName,

      MONITORING_ASSET:
        ASSET_ROOT +
        'SIAK_AOI01_O3_30B_MONITORING_2025_' +
        periodName,

      OUTPUT_ASSET:
        ASSET_ROOT +
        'SIAK_AOI01_O3_30C_ANOMALY_' +
        periodName

    });

  });

var summaryTable =
  ee.FeatureCollection(summaryFeatures);


// ==========================================================
// 9. CONSOLE
// ==========================================================

print('========================================');
print('30C-01 ANOMALI SELURUH PERIODE');
print('========================================');

print(
  'Periode yang ditampilkan:',
  DISPLAY_PERIOD
);

print(
  'Export aktif:',
  EXPORT_RESULTS
);

print(
  'Jumlah periode:',
  PERIODS.length
);

print(
  'Tabel asset:',
  summaryTable
);

print(
  'Band output:',
  displayOutput.bandNames()
);

print('========================================');
print('KETERANGAN');
print('========================================');

print(
  'ANOM_* = monitoring 2025 dikurangi baseline'
);

print(
  'DECLINE_* = hanya penurunan indeks optik'
);

print(
  'ABS_CHANGE_* = besar perubahan radar'
);

print(
  'CONFIDENCE = confidence ketersediaan data'
);

print('========================================');
print('STATUS: 30C-01 berhasil dibentuk');
print('========================================');


// ==========================================================
// 10. VISUALISASI
// ==========================================================

// NDVI anomaly:
// merah = lebih rendah dari baseline
// hijau = lebih tinggi dari baseline
Map.addLayer(
  displayOutput.select('ANOM_NDVI'),
  {
    min: -0.20,
    max: 0.20,
    palette: [
      '8B0000',
      'FF4500',
      'FFD700',
      'FFFFFF',
      '90EE90',
      '00A000',
      '004000'
    ]
  },
  '30C NDVI Anomaly ' + DISPLAY_PERIOD,
  true
);


// Penurunan NDVI:
// semakin merah = penurunan semakin besar
Map.addLayer(
  displayOutput.select('DECLINE_NDVI'),
  {
    min: 0,
    max: 0.20,
    palette: [
      'FFFFFF',
      'FFFF00',
      'FFA500',
      'FF4500',
      '8B0000'
    ]
  },
  '30C NDVI Decline ' + DISPLAY_PERIOD,
  false
);


// Anomali NDMI
Map.addLayer(
  displayOutput.select('ANOM_NDMI'),
  {
    min: -0.20,
    max: 0.20,
    palette: [
      '8B0000',
      'FF8C00',
      'FFFFFF',
      '87CEFA',
      '00008B'
    ]
  },
  '30C NDMI Anomaly ' + DISPLAY_PERIOD,
  false
);


// Perubahan VH
Map.addLayer(
  displayOutput.select('ANOM_VH_DB'),
  {
    min: -3,
    max: 3,
    palette: [
      '00008B',
      '87CEFA',
      'FFFFFF',
      'FFA07A',
      '8B0000'
    ]
  },
  '30C VH Anomaly ' + DISPLAY_PERIOD,
  false
);


// Confidence data
Map.addLayer(
  displayOutput.select('DATA_CONFIDENCE'),
  {
    min: 0,
    max: 3,
    palette: [
      '808080',
      'FF0000',
      'FFFF00',
      '00A000'
    ]
  },
  '30C Data Confidence ' + DISPLAY_PERIOD,
  false
);


// ==========================================================
// 11. EXPORT SELURUH ENAM PERIODE
// ==========================================================

if (EXPORT_RESULTS === true) {

  PERIODS.forEach(function(periodName) {

    var outputImage =
      anomalyOutputs[periodName];

    Export.image.toAsset({

      image:
        outputImage,

      description:
        'O3_30C_ANOMALY_' +
        periodName,

      assetId:
        ASSET_ROOT +
        'SIAK_AOI01_O3_30C_ANOMALY_' +
        periodName,

      region:
        geometry,

      scale:
        10,

      crs:
        'EPSG:32647',

      maxPixels:
        1e13

    });

  });

}