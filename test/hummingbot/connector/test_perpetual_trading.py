import unittest
from decimal import Decimal
from hummingbot.connector.perpetual_trading import PerpetualTrading
from hummingbot.core.event.events import PositionMode, FundingInfo, PositionSide
from hummingbot.connector.derivative.position import Position


class PerpetualTest(unittest.TestCase):

    def test_init(self):
        pt: PerpetualTrading = PerpetualTrading()
        self.assertEqual(len(pt.account_positions), 0)
        self.assertEqual(pt.position_mode, None)
        self.assertEqual(pt.funding_payment_span, [0, 0])

    def test_account_positions(self):
        """
        Test getting account positions by manually adding a position to the class member
        """
        pt: PerpetualTrading = PerpetualTrading()
        aPos: Position = Position("", PositionSide.LONG, Decimal("0"), Decimal("100"), Decimal("1"), Decimal("5"))
        pt._account_positions.append(aPos)
        self.assertEqual(len(pt.account_positions), 1)
        self.assertEqual(pt.account_positions[0], aPos)

    def test_position_mode(self):
        pt: PerpetualTrading = PerpetualTrading()
        self.assertEqual(pt.position_mode, None)
        pt.position_mode = PositionMode.ONEWAY
        self.assertEqual(pt.position_mode, PositionMode.ONEWAY)

    def test_leverage(self):
        pt: PerpetualTrading = PerpetualTrading()
        pt.set_leverage("pair1", 2)
        pt.set_leverage("pair2", 3)
        self.assertEqual(pt.get_leverage("pair1"), 2)
        self.assertEqual(pt.get_leverage("pair2"), 3)

    def test_supported_position_modes(self):
        pt: PerpetualTrading = PerpetualTrading()
        with self.assertRaises(NotImplementedError):
            pt.supported_position_modes()

    def test_funding_info(self):
        """
        Test getting funding infos by manually adding a funding info to the class member
        """
        pt: PerpetualTrading = PerpetualTrading()
        fInfo: FundingInfo = FundingInfo("pair1", Decimal(1), Decimal(2), 1000, Decimal(0.1))
        pt._funding_info["pair1"] = fInfo
        self.assertEqual(pt.get_funding_info("pair1"), fInfo)
