# VHS tape for the modelfit README demo gif.
# Install VHS: https://github.com/charmbracelet/vhs
# Regenerate:  vhs media/demo.tape   (run from the repo root)

Output media/demo.gif

Set Shell "zsh"
Set FontFamily "Menlo"
Set FontSize 15
Set Width 1160
Set Height 620
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 40ms

Type `modelfit advise "Fix this retry helper so it never sleeps after the final attempt."`
Sleep 600ms
Enter
Sleep 4000ms
Type `clear`
Enter
Sleep 500ms

Type `modelfit advise "Fix this retry helper so it never sleeps after the final attempt." --short`
Sleep 600ms
Enter
Sleep 2000ms
Type `clear`
Enter
Sleep 500ms

Type `modelfit advise "Fix this retry helper so it never sleeps after the final attempt." --explain`
Sleep 600ms
Enter
Sleep 4500ms
Type `clear`
Enter
Sleep 500ms

Type `modelfit eval`
Sleep 600ms
Enter
Sleep 6000ms
