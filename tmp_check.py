import tkinter as tk
from tkcalendar import DateEntry

def main():
    root = tk.Tk()
    root.withdraw()
    def run():
        top = tk.Toplevel(root)
        de = DateEntry(top)
        de.pack()
        root.update()
        de.drop_down()
        root.update()
        print('initial l state', de._calendar._l_month.state())
        print('initial r state', de._calendar._r_month.state())
        de._top_cal.withdraw()
        de.set_date('2024-01-01')
        root.update()
        de.destroy()
        top.destroy()
        root.update()

        top2 = tk.Toplevel(root)
        de2 = DateEntry(top2)
        de2.pack()
        root.update()
        de2.drop_down()
        root.update()
        print('second l state', de2._calendar._l_month.state())
        print('second r state', de2._calendar._r_month.state())
        de2._top_cal.withdraw()
        root.after(100, root.destroy)
    root.after(0, run)
    root.mainloop()

if __name__ == '__main__':
    main()
