# Живые обои Honeycomb и Material You

## Android 2.1–4.0

Живые обои появились в Android 2.1. `WallpaperService` создавал `Engine`, которому система передавала поверхность для отрисовки. Движок получал смещение от лаунчера через `onOffsetsChanged`, мог обрабатывать касания и останавливать отрисовку при скрытии через `onVisibilityChanged`. В демонстрационных обоях Grass фон менялся со временем суток. В i3 время внутри сцены и положение рабочего стола по горизонтали тоже управляют движением независимо. [Разбор Android Developers 2010 года](https://android-developers.googleblog.com/2010/02/live-wallpapers.html) · [WallpaperService.Engine](https://developer.android.com/reference/android/service/wallpaper/WallpaperService.Engine)

Android 3.0 Honeycomb проектировали для больших экранов. «Голографический» интерфейс подчёркивал глубину и эффекты света, а RenderScript давал средства для эффектов на обоях. В Android 4.0 Google развила Holo, впервые показанную в Honeycomb. Отсюда в коллекции широкое кадрирование, подсвеченные кромки и планы с разной глубиной. Окна фона в i3 пропускают клики, а изменения положения приходят через IPC. [Что нового в Android 3.0](https://developer.android.com/about/versions/android-3.0-highlights) · [Holo Everywhere](https://android-developers.googleblog.com/2012/01/holo-everywhere.html)

## Material You

В Android 12 цвета выбранных обоев становятся источником динамической палитры интерфейса. Material Color Utilities описывает тональные шкалы и извлечение цветов изображения. Сцены дают каждой палитре выразительные средние тона и общую гамму для неба, света и ближних объектов. В текущем окружении `m3` передаёт `matugen` один плоский кадр, поэтому палитра сохраняется на протяжении цикла анимации. Камера i3 использует пружину со скоростью, непрерывной при смене цели. [Android 12 и Material You](https://blog.google/products/android/android-12-beta/) · [Material Color Utilities](https://github.com/material-foundation/material-color-utilities) · [Пружины Material 3](https://github.com/material-components/material-components-android/blob/master/docs/theming/Motion.md)

## Процедурные референсы

| Проект | Приём, который повлиял на коллекцию |
| --- | --- |
| [Spectrawall](https://github.com/Leon-Av/spectrawall) | Повторяемое зерно по seed, преломлённые шумом полосы, усиление света на гребнях и циклическое движение. В Wallpaper-MY текстура рисуется один раз, затем XRender двигает готовые планы. |
| [Procedural Wallpapers](https://github.com/bagyoni/procedural-wallpapers) | Смещение профиля рельефа на нескольких масштабах и интерференция для воды. Здесь эти приёмы дают силуэты гор, подводный рельеф и волны на поверхности фьорда. |
| [Tessellate](https://github.com/RBahrami/Tessellate) | Порядок полупрозрачных слоёв и экспорт итоговой композиции. Комплект Wallpaper-MY добавляет к этим слоям параметры движения для i3. |

Сцены рисуются из шумовых полей, тональных градиентов и контуров. Они используют оригинальные композиции и исходный код этого репозитория.
