using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace FxConsole
{
    internal class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine(SharedCode.Greeter.Hello());
            Console.WriteLine(SharedCode.Greeter.Configuration);
        }
    }
}
