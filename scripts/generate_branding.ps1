$code = @"
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.IO;

public class BrandingGenerator
{
    public static void GenerateAll(string repoRoot)
    {
        string logoDir = Path.Combine(repoRoot, "assets", "logo");
        string bannerDir = Path.Combine(repoRoot, "assets", "banners");
        Directory.CreateDirectory(logoDir);
        Directory.CreateDirectory(bannerDir);

        GenerateIcon(Path.Combine(logoDir, "omnicapture-icon.png"), Path.Combine(logoDir, "omnicapture.ico"));
        GenerateBanner(Path.Combine(bannerDir, "omnicapture-social-preview.png"));
    }

    private static void GenerateIcon(string pngPath, string icoPath)
    {
        int size = 512;
        using (Bitmap bmp = new Bitmap(size, size))
        using (Graphics g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.PixelOffsetMode = PixelOffsetMode.HighQuality;

            // Background
            using (LinearGradientBrush bgBrush = new LinearGradientBrush(
                new Rectangle(0, 0, size, size),
                Color.FromArgb(6, 11, 20),
                Color.FromArgb(14, 27, 46),
                45f))
            {
                g.FillRectangle(bgBrush, 0, 0, size, size);
            }

            // Glow rings
            using (Pen penGlow = new Pen(Color.FromArgb(40, 0, 210, 255), 8))
            {
                g.DrawEllipse(penGlow, 32, 32, 448, 448);
            }
            using (Pen penCyan = new Pen(Color.FromArgb(255, 0, 210, 255), 5))
            {
                g.DrawEllipse(penCyan, 48, 48, 416, 416);
            }

            // Camera Lens body
            using (Pen penBlue = new Pen(Color.FromArgb(255, 0, 102, 255), 6))
            {
                g.DrawEllipse(penBlue, 140, 140, 232, 232);
            }

            // Lens Aperture
            Rectangle lensRect = new Rectangle(180, 180, 152, 152);
            using (LinearGradientBrush lensBrush = new LinearGradientBrush(
                lensRect,
                Color.FromArgb(0, 210, 255),
                Color.FromArgb(0, 102, 255),
                45f))
            {
                g.FillEllipse(lensBrush, lensRect);
            }

            // Pupil
            using (SolidBrush pupilBrush = new SolidBrush(Color.FromArgb(10, 16, 26)))
            {
                g.FillEllipse(pupilBrush, 220, 220, 72, 72);
            }

            // Glare
            using (SolidBrush highBrush = new SolidBrush(Color.FromArgb(200, 255, 255, 255)))
            {
                g.FillEllipse(highBrush, 205, 200, 24, 16);
            }

            // Target crosshair brackets
            using (Pen penArc = new Pen(Color.FromArgb(220, 0, 210, 255), 5))
            {
                penArc.StartCap = LineCap.Round;
                penArc.EndCap = LineCap.Round;

                // Top-Left
                g.DrawLine(penArc, 100, 140, 100, 100);
                g.DrawLine(penArc, 100, 100, 140, 100);

                // Top-Right
                g.DrawLine(penArc, 372, 100, 412, 100);
                g.DrawLine(penArc, 412, 100, 412, 140);

                // Bottom-Left
                g.DrawLine(penArc, 100, 372, 100, 412);
                g.DrawLine(penArc, 100, 412, 140, 412);

                // Bottom-Right
                g.DrawLine(penArc, 372, 412, 412, 412);
                g.DrawLine(penArc, 412, 372, 412, 412);
            }

            // Red recording indicator dot
            using (SolidBrush recBrush = new SolidBrush(Color.FromArgb(255, 255, 59, 48)))
            {
                g.FillEllipse(recBrush, 360, 130, 24, 24);
            }

            bmp.Save(pngPath, ImageFormat.Png);

            // Icon save
            IntPtr hIcon = bmp.GetHicon();
            using (Icon icon = Icon.FromHandle(hIcon))
            using (FileStream fs = new FileStream(icoPath, FileMode.Create))
            {
                icon.Save(fs);
            }
        }
        Console.WriteLine("Created icon at: " + pngPath);
    }

    private static void GenerateBanner(string pngPath)
    {
        int w = 1280;
        int h = 640;

        using (Bitmap bmp = new Bitmap(w, h))
        using (Graphics g = Graphics.FromImage(bmp))
        {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.ClearTypeGridFit;

            // Tech Dark background
            Rectangle bgRect = new Rectangle(0, 0, w, h);
            using (LinearGradientBrush bgBrush = new LinearGradientBrush(
                bgRect,
                Color.FromArgb(6, 10, 18),
                Color.FromArgb(12, 22, 38),
                35f))
            {
                g.FillRectangle(bgBrush, bgRect);
            }

            // Grid lines
            using (Pen gridPen = new Pen(Color.FromArgb(18, 0, 210, 255), 1))
            {
                for (int x = 0; x < w; x += 64)
                    g.DrawLine(gridPen, x, 0, x, h);
                for (int y = 0; y < h; y += 64)
                    g.DrawLine(gridPen, 0, y, w, y);
            }

            // Subtle glow
            using (Pen glow1 = new Pen(Color.FromArgb(30, 0, 210, 255), 40))
                g.DrawEllipse(glow1, 930, 130, 240, 240);
            using (Pen glow2 = new Pen(Color.FromArgb(25, 0, 102, 255), 50))
                g.DrawEllipse(glow2, 900, 100, 300, 300);

            // Large Lens on right
            int iconX = 960;
            int iconY = 180;
            Rectangle lensRect = new Rectangle(iconX, iconY, 180, 180);
            using (LinearGradientBrush lensB = new LinearGradientBrush(
                lensRect,
                Color.FromArgb(0, 210, 255),
                Color.FromArgb(0, 102, 255),
                45f))
            {
                g.FillEllipse(lensB, lensRect);
            }

            using (SolidBrush pupilB = new SolidBrush(Color.FromArgb(8, 14, 24)))
                g.FillEllipse(pupilB, iconX + 45, iconY + 45, 90, 90);

            using (SolidBrush highB = new SolidBrush(Color.FromArgb(190, 255, 255, 255)))
                g.FillEllipse(highB, iconX + 40, iconY + 35, 28, 18);

            // Target brackets around lens
            using (Pen penArc = new Pen(Color.FromArgb(200, 0, 210, 255), 4))
            {
                penArc.StartCap = LineCap.Round;
                penArc.EndCap = LineCap.Round;
                g.DrawLine(penArc, iconX - 25, iconY + 20, iconX - 25, iconY - 15);
                g.DrawLine(penArc, iconX - 25, iconY - 15, iconX + 15, iconY - 15);

                g.DrawLine(penArc, iconX + 165, iconY - 15, iconX + 205, iconY - 15);
                g.DrawLine(penArc, iconX + 205, iconY - 15, iconX + 205, iconY + 20);

                g.DrawLine(penArc, iconX - 25, iconY + 160, iconX - 25, iconY + 195);
                g.DrawLine(penArc, iconX - 25, iconY + 195, iconX + 15, iconY + 195);

                g.DrawLine(penArc, iconX + 165, iconY + 195, iconX + 205, iconY + 195);
                g.DrawLine(penArc, iconX + 205, iconY + 160, iconX + 205, iconY + 195);
            }

            // Top Cyan Accent Bar
            using (Pen barPen = new Pen(Color.FromArgb(0, 210, 255), 4))
                g.DrawLine(barPen, 95, 140, 220, 140);

            // Category tag
            using (Font catFont = new Font("Segoe UI", 12f, FontStyle.Bold))
            using (SolidBrush catBrush = new SolidBrush(Color.FromArgb(0, 210, 255)))
            {
                g.DrawString("ANDROID MIRRORING & RECORDING TOOLKIT", catFont, catBrush, 95, 155);
            }

            // Main Brand Title
            using (Font titleFont = new Font("Segoe UI", 52f, FontStyle.Bold))
            using (SolidBrush titleBrush = new SolidBrush(Color.FromArgb(255, 255, 255)))
            {
                g.DrawString("OmniCapture", titleFont, titleBrush, 88, 190);
            }

            // Subtitle Tagline
            using (Font subFont = new Font("Segoe UI", 17f, FontStyle.Regular))
            using (SolidBrush subBrush = new SolidBrush(Color.FromArgb(175, 205, 235)))
            {
                g.DrawString("High-performance screen mirroring, stealth camera capture,", subFont, subBrush, 95, 285);
                g.DrawString("direct-to-PC recording, and seamless cloud synchronization.", subFont, subBrush, 95, 320);
            }

            // Badges
            string[] badges = new string[] {
                "60 FPS Low-Latency",
                "Stealth Camera Mode",
                "Direct-to-PC MP4",
                "Wireless ADB",
                "UHID Mouse Control"
            };

            int bx = 95;
            int by = 390;
            using (Font bFont = new Font("Segoe UI", 10.5f, FontStyle.Bold))
            using (SolidBrush bTextBrush = new SolidBrush(Color.FromArgb(0, 210, 255)))
            using (SolidBrush bBgBrush = new SolidBrush(Color.FromArgb(18, 32, 54)))
            using (Pen bBorderPen = new Pen(Color.FromArgb(80, 0, 210, 255), 1))
            {
                foreach (string badge in badges)
                {
                    SizeF size = g.MeasureString(badge, bFont);
                    int bw = (int)size.Width + 24;
                    int bh = 34;

                    Rectangle bRect = new Rectangle(bx, by, bw, bh);
                    g.FillRectangle(bBgBrush, bRect);
                    g.DrawRectangle(bBorderPen, bRect);
                    g.DrawString(badge, bFont, bTextBrush, bx + 12, by + 8);

                    bx += bw + 14;
                }
            }

            // Bottom metadata / specs
            using (Font footFont = new Font("Consolas", 10.5f, FontStyle.Regular))
            using (SolidBrush footBrush = new SolidBrush(Color.FromArgb(100, 130, 160)))
            {
                g.DrawString("v1.0.0-production  |  Windows 10 / 11  |  Portable Binaries Bundled  |  Zero Setup", footFont, footBrush, 95, 560);
            }

            bmp.Save(pngPath, ImageFormat.Png);
        }
        Console.WriteLine("Created banner at: " + pngPath);
    }
}
"@

Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing
$repo = "E:\github projects\OmniCapture"
[BrandingGenerator]::GenerateAll($repo)
