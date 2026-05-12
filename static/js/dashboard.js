//static/js/dashboard.js

// Утиліти
const f2 = v => (v != null ? (+v).toFixed(2) : '—');
const f1 = v => (v != null ? (+v).toFixed(1) : '—');
const f0 = v => (v != null ? Math.round(+v) : '—');

function fmtDur(sec) {
    if (!sec || sec <= 0) return '—';
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return `${h}г ${m}хв`;
    if (m > 0) return `${m}хв ${s}с`;
    return `${s}с`;
}

// Таблиця метрик
function mv(cls, txt) {
    return `<span class="mval ${cls}">${txt}</span>`;
}
function row(name, set, metHtml) {
    return `<tr>
    <td class="pname">${name}</td>
    <td class="sval">${set}</td>
    <td>${metHtml}</td>
  </tr>`;
}
function sec(title) {
    return `<tr class="sec"><td colspan="3">${title}</td></tr>`;
}
function secOff(title) {
    return `<tr class="sec-off">
    <td colspan="3">${title}<span class="off-badge">● ВИМКНЕНО</span></td>
  </tr>
  <tr class="dis-row">
    <td colspan="3">— відстеження вимкнено в налаштуваннях —</td>
  </tr>`;
}

function buildTable(s, m) {
    if (!s) return '';
    let h = '';

    // Загальні
    h += sec('Загальні параметри');
    const spKmh = m.speed != null ? Math.round(m.speed / 100 * s.max_speed_kmh) : null;
    const spPct = spKmh != null ? spKmh / s.max_speed_kmh : 0;
    h += row('Максимальна швидкість ТЗ', s.max_speed_kmh + ' км/год',
        mv(spPct < 0.5 ? 'ok' : spPct < 0.8 ? 'warn' : 'danger',
            spKmh != null ? spKmh + ' км/год' : '—'));
    
    const brakeT = m.brake_countdown != null ? m.brake_countdown : null;
    const brakeHtml = brakeT != null && brakeT > 0
        ? mv('danger', f1(brakeT) + 'с')
        : mv('ok', '—');        
    h += row('Тривалість аварійного гальмування', s.emergency_brake_dur != null ? s.emergency_brake_dur + 'с' : '—', brakeHtml);

    const cdT = m.peace_countdown != null ? m.peace_countdown : null;
    const cdHtml = cdT != null && cdT > 0
        ? mv('warn', f1(cdT) + 'с')
        : mv('ok', '—');
    h += row('Час затримки після відміни аварійної сигналізації', s.peace_cooldown != null ? s.peace_cooldown + 'с' : '—', cdHtml);
    
    // Контроль очей
    if (!s.enable_drowsiness) {
        h += secOff('Контроль очей');
    } else {
        h += sec('Контроль очей');
        const earC = m.ear != null
            ? (m.ear > s.ear_threshold * 1.2 ? 'ok'
                : m.ear > s.ear_threshold ? 'warn' : 'danger') : 'na';
        h += row('EAR поріг закритих очей', f2(s.ear_threshold), mv(earC, f2(m.ear)));

        const eyeT = m.eye_closed_time || 0;
        const eyeC = eyeT <= 0 ? 'ok' : eyeT < s.stop_time ? 'warn' : 'danger';
        h += row('Час закриття до аварійної зупинки', s.stop_time + 'с', mv(eyeC, eyeT > 0 ? f1(eyeT) + 'с' : '—'));
    }

    // Нахил голови
    if (!s.enable_tilt) {
        h += secOff('Контроль нахилу голови');
    } else {
        h += sec('Контроль нахилу голови');
        
        // Вгору — pitch > 0
        if (m.pitch != null && m.pitch > 0) {
            const pUc = m.pitch < s.pitch_up_threshold * 0.5 ? 'ok'
                : m.pitch < s.pitch_up_threshold ? 'warn' : 'danger';
            h += row('Пороговий кут нахилу вгору', f0(s.pitch_up_threshold) + '°',
                mv(pUc, f0(m.pitch) + '°'));
        } else {
            h += row('Пороговий кут нахилу вгору', f0(s.pitch_up_threshold) + '°', mv('ok', '—'));
        }

        // Вниз — pitch < 0
        if (m.pitch != null && m.pitch < 0) {
            const absP = Math.abs(m.pitch);
            const pDc = absP < s.pitch_down_threshold * 0.5 ? 'ok'
                : absP < s.pitch_down_threshold ? 'warn' : 'danger';
            h += row('Пороговий кут нахилу вниз', f0(s.pitch_down_threshold) + '°',
                mv(pDc, f0(absP) + '°'));
        } else {
            h += row('Пороговий кут нахилу вниз', f0(s.pitch_down_threshold) + '°', mv('ok', '—'));
        }

    
        const tiltT = m.tilt_time || 0;
        const tiltC = tiltT <= 0 ? 'ok' : tiltT < s.tilt_time ? 'warn' : 'danger';
        h += row('Час нахилу голови до аварійної зупинки', s.tilt_time + 'с', mv(tiltC, tiltT > 0 ? f1(tiltT) + 'с' : '—'));
    }

    // Поворотники
    if (!s.enable_turn_signals) {
        h += secOff('Контроль повороту голови (поворотники)');
    } else {
        h += sec('Контроль повороту голови (поворотники)');

        // Лівий — yaw < 0
        if (m.yaw != null && m.yaw < 0) {
            const yLc = m.yaw < s.head_turn_angle_left * 0.5 ? 'ok'
                : m.yaw < s.head_turn_angle_left ? 'warn' : 'danger';
            h += row('Пороговий кут для лівого поворотника', f0(s.head_turn_angle_left) + '°',
                mv(yLc, f0(m.yaw) + '°'));
        } else {
            h += row('Пороговий кут для лівого поворотника', f0(s.head_turn_angle_left) + '°', mv('ok', '—'));
        }

        // Правий — yaw > 0
        if (m.yaw != null && m.yaw > 0) {
            const absYaw = Math.abs(m.yaw);
            const yRc = absYaw < s.head_turn_angle_right * 0.5 ? 'ok'
                : absYaw < s.head_turn_angle_right ? 'warn' : 'danger';
            h += row('Пороговий кут для правого поворотника', f0(s.head_turn_angle_right) + '°',
                mv(yRc, f0(absYaw) + '°'));
        } else {
            h += row('Пороговий кут для правого поворотника', f0(s.head_turn_angle_right) + '°', mv('ok', '—'));
        }

        const turnT = m.turn_signal_time != null ? m.turn_signal_time : null;
        const turnThr = s.turn_signal_delay || 0;
        const turnC = turnT == null || turnT <= 0 ? 'ok' : turnT < turnThr ? 'warn' : 'danger';
        h += row('Час повороту для ввімкнення поворотника', f1(turnThr) + 'с', mv(turnC, turnT != null && turnT > 0 ? f1(turnT) + 'с' : '—'));

        const fwdT = m.forward_gaze_time != null ? m.forward_gaze_time : null;
        const fwdThr = s.forward_gaze_cancel || 0;
        const fwdC = fwdT == null || fwdT <= 0 ? 'ok' : fwdT < fwdThr ? 'warn' : 'danger';
        h += row('Час погляду прямо для вимкнення поворотника', f1(fwdThr) + 'с', mv(fwdC, fwdT != null && fwdT > 0 ? f1(fwdT) + 'с' : '—'));
    }

    // Позіхання
    if (!s.enable_yawns) {
        h += secOff('Контроль позіхань');
    } else {
        h += sec('Контроль позіхань');

        const consY = m.consecutive_yawns || 0;
        const currentMax = m.current_max_yawns || 0;
        const yPct = currentMax > 0 ? consY / currentMax : 1;
        const yC = yPct < 0.5 ? 'ok' : yPct < 1.0 ? 'warn' : 'danger';

        // Статус обмеження — правий стовпець
        let limitHtml;
        if (m.yawn_emergency) {
            limitHtml = mv('danger', 'Аварійна зупинка!');
        } else if (currentMax > 0 && (currentMax - consY) <= 2 && consY > 0) {
            limitHtml = mv('warn', `До зупинки: ${currentMax - consY}`);
        } else {
            limitHtml = mv('ok', '—');
        }

        h += row(
            'Ліміт позіхань підряд',
            `<span class="sval">${consY} з ${currentMax}</span>`,
            limitHtml
        );

        // MAR
        const marC = m.mar != null
            ? (m.mar < s.mar_threshold * 0.6 ? 'ok'
                : m.mar < s.mar_threshold ? 'warn' : 'danger') : 'ok';
        h += row('MAR поріг позіхань', f2(s.mar_threshold), mv(marC, m.mar != null && m.mar > 0 ? f2(m.mar) : '—'));
    }
    if (!s.enable_face_missing) {
        h += secOff('Контроль зникнення обличчя');
    } else {
        h += sec('Контроль зникнення обличчя');
        const faceT = m.face_missing_time != null ? m.face_missing_time : null;
        const faceThr = s.face_missing_threshold || 0;
        const faceC = faceT == null || faceT <= 0 ? 'ok' : faceT < faceThr ? 'warn' : 'danger';
        h += row('Час відсутності обличчя до аварійної зупинки', faceThr + 'с',
            mv(faceC, faceT != null && faceT > 0 ? f1(faceT) + 'с' : '—'));
    }
    
    return h;
}

// Polling стану
let lastSeen = 0;

function setVal(id, val, warnGt, dangerGt) {
    const el = document.getElementById(id);
    el.textContent = val;
    el.className = 'stat-val' +
        (val > dangerGt ? ' danger' : val > warnGt ? ' warn' : '');
}
function sig(id, active, extra = '') {
    document.getElementById(id).className =
        `signal-badge ${extra}${active ? 'active' : ''}`.trim();
}

async function poll() {
    try {
        const r = await fetch('/state');
        if (!r.ok) throw new Error();
        const d = await r.json();
        lastSeen = Date.now();

        if (d.is_live) {
            document.getElementById('status-dot').className = 'online';
            document.getElementById('status-text').textContent = 'Онлайн';
        } else {
            document.getElementById('status-dot').className = 'stopped';
            document.getElementById('status-text').textContent = 'Зупинено';
        }

        // Водій / ТЗ
        const dr = d.driver || {};
        const veh = d.vehicle || {};
        document.getElementById('d-name').textContent =
            dr.first_name ? `${dr.first_name} ${dr.last_name}` : '—';
        document.getElementById('d-lic').textContent = dr.license_number || '—';
        document.getElementById('v-car').textContent =
            veh.make ? `${veh.make} ${veh.model} (${veh.year})` : '—';
        document.getElementById('v-plate').textContent = veh.license_plate || '—';

        // Лічильники
        setVal('s-yawns', d.yawns || 0, 2, 5);
        setVal('s-face', d.face_missing_count || 0, 0, 2);
        setVal('s-em', d.emergency_count || 0, 0, 1);

        // Сигнали
        const isHazard = d.emergency;
        sig('sig-left', d.left_signal, isHazard ? 'hazard ' : '');
        sig('sig-right', d.right_signal, isHazard ? 'hazard ' : '');
        sig('sig-em', d.emergency, 'em ');
        sig('sig-br', d.brake_active, 'br ');
        const faceEl = document.getElementById('sig-face');
        faceEl.className = 'signal-badge ' + (d.face_detected ? 'face-ok' : 'face-miss');
        faceEl.textContent = d.face_detected ? '👁 ОБЛИЧЧЯ' : '👁 ЗНИКЛО';

        // Таблиця метрик
        document.getElementById('mt-body').innerHTML = buildTable(d.settings, {
            ear: d.ear,
            mar: d.mar,
            yaw: d.yaw,
            pitch: d.pitch,
            speed: d.speed,
            eye_closed_time: d.eye_closed_time,
            tilt_time: d.tilt_time,
            consecutive_yawns: d.consecutive_yawns,
            current_max_yawns: d.current_max_yawns,
            emergency: d.emergency,
            yawn_emergency: d.yawn_emergency,
            brake_countdown: d.brake_countdown,
            emergency_cooldown: d.emergency_cooldown,
            peace_countdown: d.peace_countdown,
            peace_cooldown: d.peace_cooldown,
            turn_signal_time: d.turn_signal_time,
            forward_gaze_time: d.forward_gaze_time,
            face_missing_time: d.face_missing_time
        });

    } catch (_) {
        if (Date.now() - lastSeen > 3000) {
            document.getElementById('status-dot').className = '';
            document.getElementById('status-text').textContent = 'Офлайн';
        }
    }
}

setInterval(poll, 100);
poll();

// Статистика поїздок
async function loadStats() {
    document.getElementById('stats-tbody').innerHTML =
        '<tr><td colspan="7" class="no-data">Завантаження...</td></tr>';
    try {
        const r = await fetch('/sessions');
        if (!r.ok) throw new Error();
        renderStats(await r.json());
    } catch (_) {
        document.getElementById('stats-tbody').innerHTML =
            '<tr><td colspan="7" class="no-data">Помилка завантаження даних</td></tr>';
    }
}

function renderStats(sessions) {
    const tbody = document.getElementById('stats-tbody');
    if (!sessions || sessions.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="7" class="no-data">Немає записів про поїздки</td></tr>';
        return;
    }
    tbody.innerHTML = sessions.map((s, i) => {
        const emCls = (s.emergency_count || 0) > 0 ? 'danger' : '';
        const faceCls = (s.face_missing_count || 0) > 0 ? 'warn' : '';
        const yawnCls = (s.total_yawns || 0) > 4 ? 'warn' : '';
        const endedTxt = s.ended_at
            ? `<span style="color:#888">${s.ended_at}</span>`
            : `<span class="ok">активна</span>`;
        return `<tr>
      <td class="num">${i + 1}</td>
      <td>${s.started_at || '—'}</td>
      <td class="ctr">${endedTxt}</td>
      <td class="ctr">${fmtDur(s.duration_sec)}</td>
      <td class="ctr ${yawnCls}">${s.total_yawns || 0}</td>
      <td class="ctr ${emCls}">${s.emergency_count || 0}</td>
      <td class="ctr ${faceCls}">${s.face_missing_count || 0}</td>
    </tr>`;
    }).join('');
}

document.getElementById('stats-btn').addEventListener('click', () => {
    document.getElementById('stats-modal').classList.add('open');
    loadStats();
});
document.getElementById('stats-close').addEventListener('click', () => {
    document.getElementById('stats-modal').classList.remove('open');
});
document.getElementById('stats-refresh').addEventListener('click', loadStats);
document.getElementById('stats-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove('open');
});
