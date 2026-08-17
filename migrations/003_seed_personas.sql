-- 003_seed_personas.sql — yana ikkita persona: Sardor (1-tur qandli diabet,
-- intensiv insulin terapiyasi) va Nodira (gestatsion diabet).
--
-- Bu migratsiya PLAN.md 8-bo'limidagi arxitektura sinovi: persona qo'shish
-- faqat ma'lumot bo'lishi kerak. Birorta Python fayl o'zgartirilmaydi, va
-- hech qaysi analizator, servis yoki route bu nomlar borligini bilmaydi.
--
-- Uchta persona diabetning uchta rasmiy turini qamrab oladi — bu AI ning
-- tashxisga qarab moslashishini ko'rsatadi.
-- Izoh: o'zbekcha apostrof SQL literal ichida '' bilan yoziladi.

INSERT INTO patients (
    full_name, persona_key, diagnosis, discharge_date, phone_sim,
    doctor_id, current_day, risk_level, meta_json
) VALUES
    ('Sardor Toshmatov',
     'sardor',
     '1-tur qandli diabet — intensiv insulin terapiyasi',
     date('now'),
     '+998 90 222 33 44',
     (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
     0,
     'green',
     '{"age": 19, "diabetes_type": "1-tur", "duration_years": 6, "hba1c": 7.1, "hba1c_target": 7.0, "gfr": 112, "regimen": "intensiv_insulin", "language": "uz"}'),

    ('Nodira Karimova',
     'nodira',
     'Gestatsion diabet — homiladorlik 26-hafta',
     date('now'),
     '+998 90 333 44 55',
     (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
     0,
     'green',
     '{"age": 31, "diabetes_type": "gestatsion", "pregnancy_week": 26, "hba1c": 5.4, "hba1c_target": 6.0, "gfr": 126, "regimen": "parhez", "language": "uz"}');


-- Sardor — 1-tur, intensiv insulin terapiyasi.
-- Protokol: intensiv insulin terapiyasida kuniga kamida 4 marta o'lchash.
-- Gipoglikemiya va ketoatsidoz xavfi ikkalasi ham yuqori.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('sardor', 1, 0, 'glucose_fasting',
     'Assalomu alaykum, Sardor! Kuzatuvning 1-kuni. Nahorgi qand darajangiz qancha?',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "5.8"}'),

    ('sardor', 2, 0, 'insulin',
     'Salom, Sardor! 2-kun. Bugun insulin in''eksiyalarini o''z vaqtida qildingizmi? Doza o''zgardimi?',
     'free_text',
     '{"placeholder": "Masalan: hammasini o''z vaqtida qildim"}'),

    ('sardor', 3, 0, 'hypo_check',
     'Salom, Sardor! 3-kun. Oxirgi kunlarda titrash, terlash yoki kuchli ochlik hissi bo''ldimi? Bu gipoglikemiya belgilari.',
     'free_text',
     '{"placeholder": "Masalan: yo''q, bunday holat bo''lmadi"}'),

    ('sardor', 4, 0, 'glucose_pp',
     'Salom, Sardor! 4-kun. Ovqatdan 2 soat keyingi qand darajangiz qancha?',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "8.2"}'),

    ('sardor', 5, 0, 'wellbeing',
     'Salom, Sardor! 5-kun. Umumiy ahvolingiz qanday? Ko''ngil aynishi, qusish yoki nafasda g''alati hid bormi?',
     'free_text',
     '{"placeholder": "Masalan: hammasi yaxshi"}');


-- Nodira — gestatsion diabet.
-- Protokol: homiladorlikda maqsad qattiqroq — nahorga < 5.1 mmol/l,
-- ovqatdan 2 soat keyin < 8.5 mmol/l.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('nodira', 1, 0, 'glucose_fasting',
     'Assalomu alaykum, Nodira! Kuzatuvning 1-kuni. Nahorgi qand darajangiz qancha? Homiladorlikda maqsad — 5.1 dan past.',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "4.8"}'),

    ('nodira', 2, 0, 'glucose_pp',
     'Xayrli kun, Nodira! 2-kun. Ovqatdan 2 soat keyingi qand darajangiz qancha? Maqsad — 8.5 dan past.',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "7.2"}'),

    ('nodira', 3, 0, 'blood_pressure',
     'Salom, Nodira! 3-kun. Qon bosimingizni o''lchadingizmi? Masalan: 118/74',
     'free_text',
     '{"placeholder": "118/74"}'),

    ('nodira', 4, 0, 'swelling',
     'Salom, Nodira! 4-kun. Oyoqlaringizda yoki yuzingizda shish bormi? Bosh og''rig''i yoki ko''z xiralashishi kuzatildimi?',
     'free_text',
     '{"placeholder": "Masalan: shish yo''q, o''zimni yaxshi his qilyapman"}'),

    ('nodira', 5, 0, 'wellbeing',
     'Salom, Nodira! 5-kun. Umumiy ahvolingiz qanday? Parhezga rioya qilyapsizmi?',
     'free_text',
     '{"placeholder": "Masalan: parhezga rioya qilyapman"}');
