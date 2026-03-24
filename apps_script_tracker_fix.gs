const SHEET_ID = '1KIQjIGLSmRbffxBZF3nX5mhRkpoQSfiN3cGAGGCIh2A';
const BATCHES_SHEET = 'Batches';
const LOGS_SHEET = 'Logs';
const ANNOTATORS_SHEET = 'Annotators';

const BATCH_HEADERS = [
  'id', 'name', 'sensor', 'totalFrames', 'completed', 'startFrame',
  'End Frame', 'currentFrame', 'status', 'startDate',
  'delivered', 'deliveredDate', 'paid', 'paidDate'
];

const LOG_HEADERS = [
  'id', 'date', 'batchId', 'batchName', 'annotator',
  'workType', 'frames', 'startFrame', 'endFrame'
];

const ANNOTATOR_HEADERS = ['name'];

function doGet(e) {
  try {
    const action = (e.parameter.action || 'getAll').trim();
    const data = e.parameter.data ? JSON.parse(e.parameter.data) : {};
    let result;

    if (action === 'getAll') {
      result = {
        success: true,
        batches: readBatches_(),
        logs: readObjects_(getSheet_(LOGS_SHEET), LOG_HEADERS),
        annotators: readObjects_(getSheet_(ANNOTATORS_SHEET), ANNOTATOR_HEADERS).map(r => r.name).filter(Boolean)
      };
    } else if (action === 'saveAll') {
      writeObjects_(
        getSheet_(BATCHES_SHEET),
        BATCH_HEADERS,
        (data.batches || []).map(mapBatchForSheet_)
      );
      writeObjects_(getSheet_(LOGS_SHEET), LOG_HEADERS, data.logs || []);
      if (data.annotators) {
        writeObjects_(
          getSheet_(ANNOTATORS_SHEET),
          ANNOTATOR_HEADERS,
          (data.annotators || []).map(name => ({ name: name }))
        );
      }
      result = { success: true };
    } else if (action === 'addBatch') {
      upsertBatch_(data.batch);
      result = { success: true };
    } else if (action === 'updateBatch') {
      upsertBatch_(data.batch);
      result = { success: true };
    } else if (action === 'deleteBatch') {
      deleteById_(getSheet_(BATCHES_SHEET), String(data.id));
      deleteByField_(getSheet_(LOGS_SHEET), 'batchId', String(data.id), LOG_HEADERS);
      result = { success: true };
    } else if (action === 'updateLog') {
      upsertObject_(getSheet_(LOGS_SHEET), LOG_HEADERS, data.log);
      result = { success: true };
    } else if (action === 'addLog') {
      upsertObject_(getSheet_(LOGS_SHEET), LOG_HEADERS, data.log);
      result = { success: true };
    } else if (action === 'deleteLog') {
      deleteById_(getSheet_(LOGS_SHEET), String(data.id));
      result = { success: true };
    } else if (action === 'updateAnnotators') {
      writeObjects_(
        getSheet_(ANNOTATORS_SHEET),
        ANNOTATOR_HEADERS,
        (data.annotators || []).map(name => ({ name: name }))
      );
      result = { success: true };
    } else {
      result = { success: false, error: 'Unknown action: ' + action };
    }

    return jsonpResponse_(e, result);
  } catch (error) {
    return jsonpResponse_(e, {
      success: false,
      error: String(error)
    });
  }
}

function jsonpResponse_(e, payload) {
  const callback = e.parameter.callback;
  const output = callback
    ? callback + '(' + JSON.stringify(payload) + ')'
    : JSON.stringify(payload);

  return ContentService
    .createTextOutput(output)
    .setMimeType(
      callback
        ? ContentService.MimeType.JAVASCRIPT
        : ContentService.MimeType.JSON
    );
}

function getSheet_(name) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}

function ensureHeaders_(sheet, headers) {
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    return;
  }

  const existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  const same = headers.every(function(header, i) {
    return String(existing[i] || '').trim() === header;
  });

  if (!same) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }
}

function readObjects_(sheet, headers) {
  ensureHeaders_(sheet, headers);
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  const values = sheet.getRange(2, 1, lastRow - 1, headers.length).getValues();
  return values
    .map(function(row) {
      const obj = {};
      headers.forEach(function(header, i) {
        obj[header] = row[i];
      });
      return obj;
    })
    .filter(function(row) {
      return String(row.id || row.name || '').trim() !== '';
    });
}

function writeObjects_(sheet, headers, rows) {
  ensureHeaders_(sheet, headers);
  sheet.getRange(2, 1, Math.max(sheet.getMaxRows() - 1, 1), headers.length).clearContent();

  if (!rows.length) return;

  const values = rows.map(function(row) {
    return headers.map(function(header) {
      return row[header] !== undefined ? row[header] : '';
    });
  });

  sheet.getRange(2, 1, values.length, headers.length).setValues(values);
}

function upsertObject_(sheet, headers, obj) {
  ensureHeaders_(sheet, headers);
  const id = String(obj.id);
  const data = readObjects_(sheet, headers);
  const index = data.findIndex(function(row) {
    return String(row.id) === id;
  });

  if (index >= 0) {
    data[index] = normalizeObject_(obj, headers);
  } else {
    data.push(normalizeObject_(obj, headers));
  }

  writeObjects_(sheet, headers, data);
}

function deleteById_(sheet, id) {
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const data = readObjects_(sheet, headers).filter(function(row) {
    return String(row.id) !== String(id);
  });
  writeObjects_(sheet, headers, data);
}

function deleteByField_(sheet, field, value, headers) {
  const data = readObjects_(sheet, headers).filter(function(row) {
    return String(row[field]) !== String(value);
  });
  writeObjects_(sheet, headers, data);
}

function normalizeObject_(obj, headers) {
  const row = {};
  headers.forEach(function(header) {
    row[header] = obj && obj[header] !== undefined ? obj[header] : '';
  });
  return row;
}

function readBatches_() {
  return readObjects_(getSheet_(BATCHES_SHEET), BATCH_HEADERS).map(function(row) {
    return {
      id: row.id,
      name: row.name,
      sensor: row.sensor,
      totalFrames: row.totalFrames,
      completed: row.completed,
      startFrame: row.startFrame,
      endFrame: row['End Frame'],
      currentFrame: row.currentFrame,
      status: row.status,
      startDate: row.startDate,
      delivered: row.delivered,
      deliveredDate: row.deliveredDate,
      paid: row.paid,
      paidDate: row.paidDate
    };
  });
}

function upsertBatch_(batch) {
  const sheet = getSheet_(BATCHES_SHEET);
  ensureHeaders_(sheet, BATCH_HEADERS);
  const id = String(batch.id);
  const data = readObjects_(sheet, BATCH_HEADERS);
  const mapped = mapBatchForSheet_(batch);

  const index = data.findIndex(function(row) {
    return String(row.id) === id;
  });

  if (index >= 0) {
    data[index] = normalizeObject_(mapped, BATCH_HEADERS);
  } else {
    data.push(normalizeObject_(mapped, BATCH_HEADERS));
  }

  writeObjects_(sheet, BATCH_HEADERS, data);
}

function mapBatchForSheet_(batch) {
  return {
    id: batch.id,
    name: batch.name,
    sensor: batch.sensor,
    totalFrames: batch.totalFrames,
    completed: batch.completed,
    startFrame: batch.startFrame,
    'End Frame': batch.endFrame,
    currentFrame: batch.currentFrame,
    status: batch.status,
    startDate: batch.startDate,
    delivered: batch.delivered,
    deliveredDate: batch.deliveredDate,
    paid: batch.paid,
    paidDate: batch.paidDate
  };
}
