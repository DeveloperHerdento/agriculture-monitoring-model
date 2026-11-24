// ==========================================================
// 30B-01
// PEMBENTUKAN KOMPOSIT SENTINEL-2 DAN SENTINEL-1
// BASELINE 2020–2024 VS MONITORING 2025
//
// START_MONTH:
// 1  = Januari–Februari
// 3  = Maret–April
// 5  = Mei–Juni
// 7  = Juli–Agustus
// 9  = September–Oktober
// 11 = November–Desember
// ==========================================================


// ==========================================================
// 1. KONFIGURASI UTAMA
// ==========================================================

var START_MONTH = 11;

var BASELINE_START_YEAR = 2020;
var BASELINE_END_YEAR = 2024;
var MONITORING_YEAR = 2025;

var CLEAR_THRESHOLD = 0.60;

// Minimal clear observation Sentinel-2
// agar satu tahun dianggap valid pada suatu piksel.
var MIN_S2_CLEAR_DAYS_PER_YEAR = 2;

// Minimal jumlah tahun valid untuk baseline.
var MIN_BASELINE_VALID_YEARS = 3;

// Minimal observasi Sentinel-1 per tahun.
var MIN_S1_DATES_PER_YEAR = 3;

// false = hanya cek hasil.
// true  = membuat dua task export.
var EXPORT_RESULTS = true;

var BOUNDARY_ASSET =
  'projects/palm-oil-503202/assets/' +
  'SIAK_AOI01_PLANTATION_BOUNDARY_WEB_WGS84_2025';

var ASSET_ROOT =
  'projects/palm-oil-503202/assets/';


// ==========================================================
// 2. NAMA PERIODE
// ==========================================================

var periodNames = {
  1:  'P01_JAN_FEB',
  3:  'P02_MAR_APR',
  5:  'P03_MAY_JUN',
  7:  'P04_JUL_AUG',
  9:  'P05_SEP_OCT',
  11: 'P06_NOV_DEC'
};

var PERIOD_NAME =
  periodNames[START_MONTH];


// ==========================================================
// 3. AREA PENELITIAN
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
// 4. RENTANG SELURUH DATA
// ==========================================================

var allDataStart =
  ee.Date.fromYMD(
    BASELINE_START_YEAR,
    1,
    1
  );

var allDataEnd =
  ee.Date.fromYMD(
    MONITORING_YEAR + 1,
    1,
    1
  );


// ==========================================================
// 5. KOLEKSI SENTINEL-2 DAN CLOUD SCORE+
// ==========================================================

var sentinel2Raw =
  ee.ImageCollection(
    'COPERNICUS/S2_SR_HARMONIZED'
  )
  .filterBounds(geometry)
  .filterDate(
    allDataStart,
    allDataEnd
  );

var cloudScore =
  ee.ImageCollection(
    'GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'
  )
  .filterBounds(geometry)
  .filterDate(
    allDataStart,
    allDataEnd
  );

var sentinel2 =
  sentinel2Raw
    .linkCollection(
      cloudScore,
      ['cs_cdf']
    )
    .map(function(image) {

      return image.set(
        'ACQUISITION_DATE',
        image.date().format('YYYY-MM-dd')
      );

    });


// ==========================================================
// 6. FUNGSI MEMBUAT INDEKS SENTINEL-2
// ==========================================================

function createS2Indices(image) {

  // Cloud Score+:
  // nilai semakin tinggi berarti semakin jelas.
  var cloudMask =
    image.select('cs_cdf')
      .gte(CLEAR_THRESHOLD);

  var scl =
    image.select('SCL');

  // Mempertahankan:
  // 4 = vegetation
  // 5 = non-vegetated
  // 6 = water
  //
  // Menghapus:
  // no-data, defective, dark pixels,
  // cloud shadow, unclassified, cloud,
  // cirrus, dan snow/ice.
  var sclMask =
    scl.eq(4)
      .or(scl.eq(5))
      .or(scl.eq(6));

  var validMask =
    cloudMask.and(sclMask);

  var reflectance =
    image.select([
      'B2',
      'B4',
      'B8',
      'B8A',
      'B5',
      'B11'
    ])
    .multiply(0.0001)
    .updateMask(validMask);

  var blue =
    reflectance.select('B2');

  var red =
    reflectance.select('B4');

  var nir =
    reflectance.select('B8');

  var narrowNir =
    reflectance.select('B8A');

  var redEdge =
    reflectance.select('B5');

  var swir1 =
    reflectance.select('B11');


  // NDVI
  var ndvi =
    nir.subtract(red)
      .divide(
        nir.add(red)
      )
      .rename('NDVI');


  // EVI
  var evi =
    nir.subtract(red)
      .multiply(2.5)
      .divide(
        nir
          .add(red.multiply(6))
          .subtract(blue.multiply(7.5))
          .add(1)
      )
      .rename('EVI');


  // MSAVI
  var msaviTerm =
    nir.multiply(2).add(1);

  var msaviInside =
    msaviTerm.pow(2)
      .subtract(
        nir.subtract(red)
          .multiply(8)
      )
      .max(0);

  var msavi =
    msaviTerm
      .subtract(
        msaviInside.sqrt()
      )
      .divide(2)
      .rename('MSAVI');


  // NDRE
  // Resolusi asli B8A dan B5 = 20 meter.
  var ndre =
    narrowNir.subtract(redEdge)
      .divide(
        narrowNir.add(redEdge)
      )
      .rename('NDRE')
      .resample('bilinear');


  // NDMI
  // Resolusi asli B8A dan B11 = 20 meter.
  var ndmi =
    narrowNir.subtract(swir1)
      .divide(
        narrowNir.add(swir1)
      )
      .rename('NDMI')
      .resample('bilinear');


  // Band valid digunakan untuk menghitung
  // jumlah observasi bersih per piksel.
  var valid =
    ee.Image.constant(1)
      .rename('VALID')
      .updateMask(validMask)
      .toByte();


  return ee.Image.cat([
      ndvi,
      evi,
      msavi,
      ndre,
      ndmi,
      valid
    ])
    .copyProperties(
      image,
      ['system:time_start']
    );

}


// ==========================================================
// 7. SENTINEL-2 MOSAIK PER TANGGAL
// ==========================================================

function getDailyS2Collection(year) {

  year =
    ee.Number(year);

  var periodStart =
    ee.Date.fromYMD(
      year,
      START_MONTH,
      1
    );

  var periodEnd =
    periodStart.advance(
      2,
      'month'
    );

  var periodCollection =
    sentinel2.filterDate(
      periodStart,
      periodEnd
    );

  var uniqueDates =
    ee.List(
      periodCollection.aggregate_array(
        'ACQUISITION_DATE'
      )
    )
    .distinct()
    .sort();

  var dailyImages =
    uniqueDates.map(function(dateText) {

      dateText =
        ee.String(dateText);

      var date =
        ee.Date(dateText);

      // Mengambil piksel dengan nilai
      // Cloud Score+ terbaik pada tanggal tersebut.
      var dailyMosaic =
        periodCollection
          .filterDate(
            date,
            date.advance(1, 'day')
          )
          .qualityMosaic('cs_cdf');

      return createS2Indices(
        dailyMosaic
      )
      .set({
        YEAR:
          year,

        ACQUISITION_DATE:
          dateText,

        'system:time_start':
          date.millis()
      });

    });

  return ee.ImageCollection.fromImages(
    dailyImages
  );

}


// ==========================================================
// 8. KOMPOSIT SENTINEL-2 PER TAHUN
// ==========================================================

var S2_INDEX_BANDS = [
  'NDVI',
  'EVI',
  'MSAVI',
  'NDRE',
  'NDMI'
];

function buildAnnualS2Composite(year) {

  year =
    ee.Number(year);

  var dailyCollection =
    getDailyS2Collection(year);

  var clearDays =
    dailyCollection
      .select('VALID')
      .count()
      .rename('S2_CLEAR_DAYS');

  var validYear =
    clearDays
      .gte(
        MIN_S2_CLEAR_DAYS_PER_YEAR
      )
      .unmask(0)
      .rename('VALID_YEAR')
      .toByte();

  var annualComposite =
    dailyCollection
      .select(S2_INDEX_BANDS)
      .median()
      .updateMask(validYear);

  return annualComposite
    .addBands(clearDays)
    .addBands(validYear)
    .set({
      YEAR:
        year,

      S2_DATE_COUNT:
        dailyCollection.size()
    });

}


// ==========================================================
// 9. SENTINEL-2 BASELINE 2020–2024
// ==========================================================

var baselineYears =
  ee.List.sequence(
    BASELINE_START_YEAR,
    BASELINE_END_YEAR
  );

var annualS2Baseline =
  ee.ImageCollection.fromImages(

    baselineYears.map(function(year) {

      return buildAnnualS2Composite(
        year
      );

    })

  );

var s2BaselineValidYears =
  annualS2Baseline
    .select('VALID_YEAR')
    .sum()
    .rename('S2_BASE_VALID_YEARS');

var s2Baseline =
  annualS2Baseline
    .select(S2_INDEX_BANDS)
    .median()
    .updateMask(
      s2BaselineValidYears.gte(
        MIN_BASELINE_VALID_YEARS
      )
    )
    .rename([
      'S2_BASE_NDVI',
      'S2_BASE_EVI',
      'S2_BASE_MSAVI',
      'S2_BASE_NDRE',
      'S2_BASE_NDMI'
    ]);


// ==========================================================
// 10. SENTINEL-2 MONITORING 2025
// ==========================================================

var annualS2Monitoring =
  buildAnnualS2Composite(
    MONITORING_YEAR
  );

var s2Monitoring =
  annualS2Monitoring
    .select(S2_INDEX_BANDS)
    .rename([
      'S2_MON_NDVI',
      'S2_MON_EVI',
      'S2_MON_MSAVI',
      'S2_MON_NDRE',
      'S2_MON_NDMI'
    ]);

var s2MonitoringClearDays =
  annualS2Monitoring
    .select('S2_CLEAR_DAYS')
    .rename('S2_MON_CLEAR_DAYS');


// ==========================================================
// 11. KOLEKSI SENTINEL-1 ASCENDING
// ==========================================================

var sentinel1 =
  ee.ImageCollection(
    'COPERNICUS/S1_GRD'
  )
  .filterBounds(geometry)
  .filterDate(
    allDataStart,
    allDataEnd
  )
  .filter(
    ee.Filter.eq(
      'instrumentMode',
      'IW'
    )
  )
  .filter(
    ee.Filter.eq(
      'resolution_meters',
      10
    )
  )
  .filter(
    ee.Filter.eq(
      'orbitProperties_pass',
      'ASCENDING'
    )
  )
  .filter(
    ee.Filter.listContains(
      'transmitterReceiverPolarisation',
      'VV'
    )
  )
  .filter(
    ee.Filter.listContains(
      'transmitterReceiverPolarisation',
      'VH'
    )
  )
  .map(function(image) {

    return image.set(
      'ACQUISITION_DATE',
      image.date().format('YYYY-MM-dd')
    );

  });


// ==========================================================
// 12. FUNGSI PARAMETER SENTINEL-1
// ==========================================================

function createS1Parameters(image) {

  var angle =
    image.select('angle');

  // Mengurangi kemungkinan border noise.
  var angleMask =
    angle.gt(30)
      .and(
        angle.lt(45)
      );

  var vvDb =
    image.select('VV')
      .rename('VV_DB');

  var vhDb =
    image.select('VH')
      .rename('VH_DB');

  var vvMinusVh =
    vvDb.subtract(vhDb)
      .rename('VV_MINUS_VH_DB');


  // Konversi dB menjadi linear.
  var vvLinear =
    ee.Image.constant(10)
      .pow(
        vvDb.divide(10)
      );

  var vhLinear =
    ee.Image.constant(10)
      .pow(
        vhDb.divide(10)
      );


  // Radar Vegetation Index.
  var rvi =
    vhLinear.multiply(4)
      .divide(
        vvLinear.add(vhLinear)
      )
      .rename('S1_RVI');


  var valid =
    ee.Image.constant(1)
      .rename('VALID')
      .updateMask(angleMask)
      .toByte();


  return ee.Image.cat([
      vvDb,
      vhDb,
      vvMinusVh,
      rvi,
      valid
    ])
    .updateMask(angleMask)
    .copyProperties(
      image,
      [
        'system:time_start',
        'relativeOrbitNumber_start'
      ]
    );

}


// ==========================================================
// 13. SENTINEL-1 MOSAIK PER TANGGAL
// ==========================================================

function getDailyS1Collection(year) {

  year =
    ee.Number(year);

  var periodStart =
    ee.Date.fromYMD(
      year,
      START_MONTH,
      1
    );

  var periodEnd =
    periodStart.advance(
      2,
      'month'
    );

  var periodCollection =
    sentinel1.filterDate(
      periodStart,
      periodEnd
    );

  var uniqueDates =
    ee.List(
      periodCollection.aggregate_array(
        'ACQUISITION_DATE'
      )
    )
    .distinct()
    .sort();

  var dailyImages =
    uniqueDates.map(function(dateText) {

      dateText =
        ee.String(dateText);

      var date =
        ee.Date(dateText);

      var dailyComposite =
        periodCollection
          .filterDate(
            date,
            date.advance(1, 'day')
          )
          .map(createS1Parameters)
          .median();

      return dailyComposite.set({
        YEAR:
          year,

        ACQUISITION_DATE:
          dateText,

        'system:time_start':
          date.millis()
      });

    });

  return ee.ImageCollection.fromImages(
    dailyImages
  );

}


// ==========================================================
// 14. KOMPOSIT SENTINEL-1 PER TAHUN
// ==========================================================

var S1_PARAMETER_BANDS = [
  'VV_DB',
  'VH_DB',
  'VV_MINUS_VH_DB',
  'S1_RVI'
];

function buildAnnualS1Composite(year) {

  year =
    ee.Number(year);

  var dailyCollection =
    getDailyS1Collection(year);

  var dateCount =
    dailyCollection
      .select('VALID')
      .count()
      .rename('S1_DATE_COUNT');

  var validYear =
    dateCount
      .gte(
        MIN_S1_DATES_PER_YEAR
      )
      .unmask(0)
      .rename('VALID_YEAR')
      .toByte();

  var annualComposite =
    dailyCollection
      .select(S1_PARAMETER_BANDS)
      .median()
      .updateMask(validYear);

  return annualComposite
    .addBands(dateCount)
    .addBands(validYear)
    .set({
      YEAR:
        year,

      S1_DATE_COUNT_PROPERTY:
        dailyCollection.size()
    });

}


// ==========================================================
// 15. SENTINEL-1 BASELINE 2020–2024
// ==========================================================

var annualS1Baseline =
  ee.ImageCollection.fromImages(

    baselineYears.map(function(year) {

      return buildAnnualS1Composite(
        year
      );

    })

  );

var s1BaselineValidYears =
  annualS1Baseline
    .select('VALID_YEAR')
    .sum()
    .rename('S1_BASE_VALID_YEARS');

var s1Baseline =
  annualS1Baseline
    .select(S1_PARAMETER_BANDS)
    .median()
    .updateMask(
      s1BaselineValidYears.gte(
        MIN_BASELINE_VALID_YEARS
      )
    )
    .rename([
      'S1_BASE_VV_DB',
      'S1_BASE_VH_DB',
      'S1_BASE_VV_MINUS_VH_DB',
      'S1_BASE_RVI'
    ]);


// ==========================================================
// 16. SENTINEL-1 MONITORING 2025
// ==========================================================

var annualS1Monitoring =
  buildAnnualS1Composite(
    MONITORING_YEAR
  );

var s1Monitoring =
  annualS1Monitoring
    .select(S1_PARAMETER_BANDS)
    .rename([
      'S1_MON_VV_DB',
      'S1_MON_VH_DB',
      'S1_MON_VV_MINUS_VH_DB',
      'S1_MON_RVI'
    ]);

var s1MonitoringDateCount =
  annualS1Monitoring
    .select('S1_DATE_COUNT')
    .rename('S1_MON_DATE_COUNT');


// ==========================================================
// 17. OUTPUT FINAL
// ==========================================================

var baselineOutput =
  ee.Image.cat([
      s2Baseline,
      s2BaselineValidYears,
      s1Baseline,
      s1BaselineValidYears
    ])
    .toFloat()
    .clip(geometry)
    .set({
      AOI_ID:
        'SIAK_AOI01',

      PERIOD:
        PERIOD_NAME,

      BASELINE_START_YEAR:
        BASELINE_START_YEAR,

      BASELINE_END_YEAR:
        BASELINE_END_YEAR,

      S2_CLEAR_THRESHOLD:
        CLEAR_THRESHOLD,

      MIN_BASELINE_VALID_YEARS:
        MIN_BASELINE_VALID_YEARS
    });


var monitoringOutput =
  ee.Image.cat([
      s2Monitoring,
      s2MonitoringClearDays,
      s1Monitoring,
      s1MonitoringDateCount
    ])
    .toFloat()
    .clip(geometry)
    .set({
      AOI_ID:
        'SIAK_AOI01',

      PERIOD:
        PERIOD_NAME,

      MONITORING_YEAR:
        MONITORING_YEAR,

      S2_CLEAR_THRESHOLD:
        CLEAR_THRESHOLD
    });


// ==========================================================
// 18. TABEL QA
// ==========================================================

var qaYears =
  ee.List.sequence(
    BASELINE_START_YEAR,
    MONITORING_YEAR
  );

var qaTable =
  ee.FeatureCollection(

    qaYears.map(function(year) {

      year =
        ee.Number(year);

      return ee.Feature(null, {

        YEAR:
          year,

        PERIOD:
          PERIOD_NAME,

        S2_DAILY_COMPOSITE_COUNT:
          getDailyS2Collection(
            year
          ).size(),

        S1_DAILY_COMPOSITE_COUNT:
          getDailyS1Collection(
            year
          ).size()

      });

    })

  );


// ==========================================================
// 19. CONSOLE
// ==========================================================

print('========================================');
print('30B-01 KOMPOSIT S2 + S1');
print('========================================');

print(
  'Periode:',
  PERIOD_NAME
);

print(
  'Export aktif:',
  EXPORT_RESULTS
);

print(
  'Tabel QA tanggal:',
  qaTable
);

print(
  'Band baseline:',
  baselineOutput.bandNames()
);

print(
  'Band monitoring:',
  monitoringOutput.bandNames()
);

print('========================================');
print('STATUS: 30B-01 berhasil dibentuk');
print('========================================');


// ==========================================================
// 20. VISUALISASI
// ==========================================================

Map.addLayer(
  s2Baseline
    .select('S2_BASE_NDVI')
    .clip(geometry),
  {
    min: 0.2,
    max: 0.9,
    palette: [
      '8B4513',
      'F5DEB3',
      'FFFF00',
      '7CFC00',
      '006400'
    ]
  },
  'Baseline NDVI ' + PERIOD_NAME,
  false
);


Map.addLayer(
  s2Monitoring
    .select('S2_MON_NDVI')
    .clip(geometry),
  {
    min: 0.2,
    max: 0.9,
    palette: [
      '8B4513',
      'F5DEB3',
      'FFFF00',
      '7CFC00',
      '006400'
    ]
  },
  'Monitoring NDVI 2025 ' + PERIOD_NAME,
  true
);


Map.addLayer(
  s2MonitoringClearDays
    .clip(geometry),
  {
    min: 0,
    max: 10,
    palette: [
      '8B0000',
      'FFA500',
      'FFFF00',
      '90EE90',
      '006400'
    ]
  },
  'S2 Clear Days 2025 ' + PERIOD_NAME,
  false
);


Map.addLayer(
  s1Baseline
    .select('S1_BASE_VH_DB')
    .clip(geometry),
  {
    min: -25,
    max: -8
  },
  'Baseline S1 VH ' + PERIOD_NAME,
  false
);


Map.addLayer(
  s1Monitoring
    .select('S1_MON_VH_DB')
    .clip(geometry),
  {
    min: -25,
    max: -8
  },
  'Monitoring S1 VH 2025 ' + PERIOD_NAME,
  false
);


// ==========================================================
// 21. EXPORT KE ASSET
// ==========================================================

if (EXPORT_RESULTS === true) {

  Export.image.toAsset({

    image:
      baselineOutput,

    description:
      'O3_30B_BASELINE_' +
      PERIOD_NAME,

    assetId:
      ASSET_ROOT +
      'SIAK_AOI01_O3_30B_BASELINE_' +
      PERIOD_NAME,

    region:
      geometry,

    scale:
      10,

    crs:
      'EPSG:32647',

    maxPixels:
      1e13

  });


  Export.image.toAsset({

    image:
      monitoringOutput,

    description:
      'O3_30B_MONITORING_2025_' +
      PERIOD_NAME,

    assetId:
      ASSET_ROOT +
      'SIAK_AOI01_O3_30B_MONITORING_2025_' +
      PERIOD_NAME,

    region:
      geometry,

    scale:
      10,

    crs:
      'EPSG:32647',

    maxPixels:
      1e13

  });

}