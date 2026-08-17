-- 002_seed_demo.sql — demo ma'lumotlari: bitta shifokor, bemor Bobur
-- (2-tur qandli diabet) va 5 kunlik kuzatuv savollari.
--
-- Loyihaning asosiy yo'nalishi — qandli diabet. Savollar va chegaralar
-- O'zR SSV 2025-yil 23-iyundagi 180-sonli buyrug'iga ilova qilingan
-- «2-tur qandli diabet» milliy klinik protokolidan olingan.
--
-- Persona yoki savol qo'shish keyinchalik YANGI seed migratsiyasi bilan
-- bajariladi, Python o'zgartirilmaydi (PLAN.md 1-tamoyil).
-- Izoh: o'zbekcha apostrof SQL literal ichida '' bilan yoziladi.

INSERT INTO doctors (full_name, clinic_name, phone_sim) VALUES
    ('Dilnoza Karimova', 'Qarshi shahar 3-son OSHP', '+998 90 123 45 67');

INSERT INTO patients (
    full_name, persona_key, diagnosis, discharge_date, phone_sim,
    doctor_id, current_day, risk_level, meta_json
) VALUES (
    'Bobur Aliyev',
    'bobur',
    '2-tur qandli diabet — 8 yil, SBK C2 A2',
    date('now'),
    '+998 90 111 22 33',
    (SELECT id FROM doctors WHERE full_name = 'Dilnoza Karimova'),
    0,
    'green',
    '{"age": 52, "diabetes_type": "2-tur", "duration_years": 8, "ckd_stage": "C2", "albuminuria": "A2", "hba1c": 8.4, "hba1c_target": 7.0, "gfr": 74, "regimen": "peroral", "language": "uz"}'
);

-- Bobur uchun besh kunlik kuzatuv savollari.
-- Protokol: peroral terapiyada kuniga kamida 1 marta turli vaqtlarda
-- o'lchash + haftada 1 glikemik profil. Qon bosimi har kuni.
INSERT INTO checkin_templates
    (persona_key, day_offset, seq, question_key, question_text, answer_type, config_json)
VALUES
    ('bobur', 1, 0, 'glucose_fasting',
     'Assalomu alaykum, Bobur aka! Kuzatuvning 1-kuni. Bugun nahorgi qand darajangiz qancha? Masalan: 6.4',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "6.4"}'),

    ('bobur', 2, 0, 'blood_pressure',
     'Xayrli kun, Bobur aka! 2-kun. Bugun qon bosimingizni o''lchadingizmi? Masalan: 128/82',
     'free_text',
     '{"placeholder": "128/82"}'),

    ('bobur', 3, 0, 'glucose_pp',
     'Salom, Bobur aka! 3-kun. Ovqatdan 2 soat keyingi qand darajangiz qancha? Masalan: 9.1',
     'number',
     '{"unit": "mmol/l", "min": 1, "max": 40, "placeholder": "9.1"}'),

    ('bobur', 4, 0, 'medication',
     'Salom, Bobur aka! 4-kun. Bugun dorilaringizni belgilangan vaqtda qabul qildingizmi? Metformin va glimepirid.',
     'free_text',
     '{"placeholder": "Masalan: hammasini ichdim"}'),

    ('bobur', 5, 0, 'wellbeing',
     'Salom, Bobur aka! 5-kun. Umumiy ahvolingiz qanday? Chanqash, tez-tez siyish, holsizlik yoki boshqa shikoyat bormi?',
     'free_text',
     '{"placeholder": "Masalan: shikoyat yo''q, o''zimni yaxshi his qilyapman"}');
